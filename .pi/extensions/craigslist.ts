/**
 * Craigslist Search Assistant Extension
 *
 * Wraps the CraigslistSearchPython project with tools and commands that make
 * it easy to iteratively search for items, review results, and refine scoring.
 *
 * Workflow:
 *   1. /cl-new → guided setup, creates a YAML config
 *   2. LLM calls craigslist_fetch  → fetches listings (slow, ~5s per request)
 *   3. LLM calls craigslist_display → ranks, generates HTML, opens browser
 *   4. User reviews, gives feedback → LLM edits scoring in the YAML config
 *   5. LLM calls craigslist_display again (no re-fetch) → see new ranking
 *   6. Repeat 4–5 until happy
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { truncateTail, DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES, formatSize } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

// ──────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────

const PROJECT_DIR = "/Users/nigel/Git/CraigslistSearchPython";

const SYSTEM_PROMPT_ADDITION = `
## Craigslist Search Assistant

You help the user search Craigslist for items using the scraper project at ${PROJECT_DIR}.

### Iteration workflow
1. Create a YAML config in \`${PROJECT_DIR}/config/\` that captures what the user wants
2. Call \`craigslist_fetch\` to retrieve listings — this is **slow** (~5 s per listing), be patient and let it run
3. Call \`craigslist_display\` to re-rank and generate an HTML report (opens automatically in browser)
4. User reviews the HTML results and gives feedback
5. Edit the scoring rules in the YAML config using the \`edit\` or \`write\` tool
6. Call \`craigslist_display\` again — no re-fetch needed, just new ranking
7. Repeat steps 4–6 until the user is happy

### YAML config format
\`\`\`yaml
searches:
  search_name:                      # used as key; one search per file
    query: "search term"            # what Craigslist will search for
    categories: ["cta", "pta"]      # see list below
    cities: ["sfbay", "losangeles"] # see list below
    max_pages: 3                    # pages per city × category
    listing_type: "vehicle"         # "vehicle" for cars; "base" for parts/general

    storage:
      filename: "search_name.json"  # stored in data/

    scoring:
      - keywords: ["word1", "word2"]
        points: 25                  # positive = good; negative = bad
        match: title                # "title", "description", or omit = both
        match_type: whole           # "whole" (word boundary) or "partial"

      - keywords: ["conditional"]
        points: 10
        requires: ["must also appear"]    # only score when all present
        excludes: ["if present, skip"]    # never score when any present

    deduplication:
      enabled: true
      similarity_threshold: 0.85
      min_title_length: 30
      max_age_days: 90
\`\`\`

### Categories
| Code | Meaning |
|------|---------|
| cta  | Cars/trucks by owner |
| ctd  | Cars/trucks by dealer |
| pta  | Auto parts by owner |
| mca  | Motorcycles by owner |
| boo  | Boats by owner |
| sss  | General for sale |

### Common cities
sfbay, losangeles, seattle, portland, denver, chicago, newyork, boston, austin, phoenix,
sandiego, sacramento, fresno, bakersfield, orangecounty, inland empire, ventura

### Scoring tips
- Positive points: desirable features (manual, low miles, clean title, first gen, etc.)
- Negative points: red flags (salvage, dealer, needs work, flood damage, shipping)
- Use \`match: title\` + \`match_type: whole\` to avoid false positives
- Use \`requires\` / \`excludes\` for conditional rules
- See \`${PROJECT_DIR}/config/subaru_forester.yaml\` as a reference example

### Config path convention
Always pass config paths relative to the project root, e.g. \`config/my_search.yaml\`.
`;

// ──────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────

/** Run a Python command in the project directory, streaming stdout/stderr via onUpdate. */
function runPython(
  args: string[],
  signal: AbortSignal | undefined,
  onUpdate?: (partial: { content: Array<{ type: "text"; text: string }> }) => void,
): Promise<{ output: string; exitCode: number }> {
  return new Promise((resolve, reject) => {
    const proc = spawn("python3", ["main.py", ...args], {
      cwd: PROJECT_DIR,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let output = "";
    let lastUpdate = Date.now();

    const flush = () => {
      if (onUpdate && output) {
        onUpdate({ content: [{ type: "text", text: output }] });
      }
    };

    const onData = (chunk: Buffer) => {
      output += chunk.toString();
      const now = Date.now();
      if (now - lastUpdate > 800) {
        lastUpdate = now;
        flush();
      }
    };

    proc.stdout.on("data", onData);
    proc.stderr.on("data", onData);

    proc.on("close", (code) => {
      flush(); // final update
      resolve({ output, exitCode: code ?? 0 });
    });

    proc.on("error", reject);

    if (signal) {
      signal.addEventListener("abort", () => proc.kill("SIGTERM"), { once: true });
    }
  });
}

/** Open a file in the system default app (browser for HTML). */
function openFile(filePath: string): void {
  spawn("open", [filePath], { detached: true, stdio: "ignore" }).unref();
}

/** Derive a stable output HTML path from the config path.
 *  e.g. "config/honda_ridgeline.yaml" → "outputs/results/honda_ridgeline.html" */
function configToOutputPath(configPath: string): string {
  const name = configPath.replace(/^.*[\/\\]/, "").replace(/\.ya?ml$/i, "");
  return `outputs/results/${name}.html`;
}

/** Extract the HTML output path from command output (looks for the saved path line). */
function extractHtmlPath(output: string): string | undefined {
  const match = output.match(/HTML saved to:\s*(.+\.html)/);
  return match?.[1]?.trim();
}

// ──────────────────────────────────────────────────────────
// Progress parsing
// ──────────────────────────────────────────────────────────

interface FetchProgress {
  phase: "searching" | "fetching" | "done";
  city?: string;          // e.g. "sfbay/cta"
  step?: string;          // e.g. "[2/4]"
  lastUrl?: string;       // just the path portion of the URL
  saved: number;          // listings saved so far
  total?: number;         // final count when done
  elapsed?: number;       // seconds since start
}

function parseProgress(output: string, startTime: number): FetchProgress {
  // Done?
  const doneMatch = output.match(/✅ Fetched (\d+) new listings/);
  if (doneMatch) {
    return {
      phase: "done",
      total: parseInt(doneMatch[1]),
      saved: parseInt(doneMatch[1]),
      elapsed: (Date.now() - startTime) / 1000,
    };
  }

  // Current city/category
  const cityMatches = [...output.matchAll(/🔍 Processing ([\w\/]+)/g)];
  const city = cityMatches[cityMatches.length - 1]?.[1];

  // Progress step [N/M]
  const stepMatches = [...output.matchAll(/\[(\d+)\/(\d+)\]/g)];
  const stepMatch = stepMatches[stepMatches.length - 1];
  const step = stepMatch ? `[${stepMatch[1]}/${stepMatch[2]}]` : undefined;

  // Last URL fetched — just keep the path so it fits on one line
  const urlMatches = [...output.matchAll(/🌐 Fetching: (https?:\/\/[^\n\r]+)/g)];
  const rawUrl = urlMatches[urlMatches.length - 1]?.[1]?.trim();
  let lastUrl: string | undefined;
  if (rawUrl) {
    try {
      lastUrl = new URL(rawUrl).pathname;
    } catch {
      lastUrl = rawUrl.slice(0, 80);
    }
  }

  // Saved count
  const savedMatches = [...output.matchAll(/💾 Saved (\d+) listings/g)];
  const saved = savedMatches.length > 0
    ? parseInt(savedMatches[savedMatches.length - 1][1])
    : 0;

  const phase = step ? "fetching" : "searching";
  return { phase, city, step, lastUrl, saved, elapsed: (Date.now() - startTime) / 1000 };
}

/** Find the most recently modified HTML in outputs/results/. */
function latestResultHtml(): string | undefined {
  const dir = join(PROJECT_DIR, "outputs", "results");
  if (!existsSync(dir)) return undefined;
  const files = readdirSync(dir)
    .filter((f) => f.endsWith(".html"))
    .map((f) => ({ name: f, mtime: statSync(join(dir, f)).mtime.getTime() }))
    .sort((a, b) => b.mtime - a.mtime);
  return files[0] ? join(dir, files[0].name) : undefined;
}

// ──────────────────────────────────────────────────────────
// Extension factory
// ──────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {

  // ── System prompt injection ──────────────────────────────
  pi.on("before_agent_start", (_event, _ctx) => {
    return { systemPrompt: _event.systemPrompt + "\n" + SYSTEM_PROMPT_ADDITION };
  });

  // ── Tool: craigslist_fetch ───────────────────────────────
  pi.registerTool({
    name: "craigslist_fetch",
    label: "Fetch Craigslist",
    description:
      "Fetch Craigslist listings using the scraper. " +
      "This is SLOW (~5 s per listing) — call it once and iterate on scoring with craigslist_display. " +
      "Pass a config path relative to the project root (e.g. 'config/subaru_forester.yaml').",
    promptSnippet: "Fetch Craigslist listings from live search pages",
    promptGuidelines: [
      "Use craigslist_fetch once to retrieve listings, then iterate scoring with craigslist_display — never re-fetch just to re-rank.",
      "Always warn the user that craigslist_fetch is slow before calling it.",
    ],
    parameters: Type.Object({
      config: Type.String({
        description: "Config file path relative to project root (e.g. 'config/my_search.yaml')",
      }),
      limit: Type.Optional(
        Type.Number({
          description: "Max listings to fetch (omit for unlimited)",
        }),
      ),
      clear: Type.Optional(
        Type.Boolean({
          description: "Clear existing storage before fetching (start fresh)",
          default: false,
        }),
      ),
      save_raw: Type.Optional(
        Type.Boolean({
          description: "Save raw HTML files for later re-parsing",
          default: false,
        }),
      ),
    }),

    async execute(_toolCallId, params, signal, onUpdate, ctx) {
      const args: string[] = ["--config", params.config, "--fetch"];
      if (params.limit && params.limit > 0) args.push(String(params.limit));
      if (params.clear) args.push("--clear");
      if (params.save_raw) args.push("--save-raw");

      const startTime = Date.now();
      ctx.ui.setStatus("craigslist", "⏳ craigslist: starting fetch…");

      // Wrap onUpdate to also refresh the footer status
      const trackingUpdate = (partial: { content: Array<{ type: "text"; text: string }> }) => {
        const p = parseProgress(partial.content[0]?.text ?? "", startTime);
        if (p.phase === "searching") {
          ctx.ui.setStatus("craigslist",
            `🔍 craigslist: scanning ${p.city ?? "search pages"}…`);
        } else if (p.phase === "fetching") {
          ctx.ui.setStatus("craigslist",
            `⬇️  craigslist: ${p.step} saved ${p.saved}  ${p.lastUrl ?? ""}`);
        }
        onUpdate?.(partial);
      };

      let output = "";
      let exitCode = 0;
      try {
        ({ output, exitCode } = await runPython(args, signal, trackingUpdate));
      } finally {
        ctx.ui.setStatus("craigslist", undefined);
      }

      // Truncate if very large
      const truncation = truncateTail(output, {
        maxLines: DEFAULT_MAX_LINES,
        maxBytes: DEFAULT_MAX_BYTES,
      });

      let result = truncation.content;
      if (truncation.truncated) {
        result += `\n\n[Output truncated: showing last ${truncation.outputLines} of ${truncation.totalLines} lines (${formatSize(truncation.outputBytes)} of ${formatSize(truncation.totalBytes)})]`;
      }

      if (exitCode !== 0) {
        throw new Error(`Fetch failed (exit ${exitCode}):\n${result}`);
      }

      const finalProgress = parseProgress(output, startTime);
      return {
        content: [{ type: "text", text: result }],
        details: { config: params.config, exitCode, progress: finalProgress },
      };
    },

    renderCall(args, theme, _context) {
      let text = theme.fg("toolTitle", theme.bold("craigslist_fetch "));
      text += theme.fg("accent", args.config);
      if (args.limit) text += theme.fg("muted", ` · limit ${args.limit}`);
      if (args.clear) text += theme.fg("warning", " · clear storage");
      if (args.save_raw) text += theme.fg("dim", " · save-raw");
      return new Text(text, 0, 0);
    },

    renderResult(result, { isPartial }, theme, context) {
      // ── While running: show live progress ─────────────────
      if (isPartial) {
        const raw = (result.content[0] as { type: string; text?: string } | undefined)?.text ?? "";
        const p = parseProgress(raw, (context.state as { startTime?: number }).startTime ?? Date.now());

        if (p.phase === "searching") {
          let text = theme.fg("warning", "⏳ Scanning search pages");
          if (p.city) text += theme.fg("muted", `  ${p.city}`);
          return new Text(text, 0, 0);
        }

        // fetching phase
        let text = theme.fg("warning", `⬇️  Fetching listings`);
        if (p.step) text += theme.fg("accent", `  ${p.step}`);
        if (p.saved > 0) text += theme.fg("success", `  ✓ ${p.saved} saved`);
        if (p.lastUrl) text += "\n" + theme.fg("dim", `   ${p.lastUrl}`);
        return new Text(text, 0, 0);
      }

      // ── Done: show summary ────────────────────────────────
      const details = result.details as { progress?: FetchProgress } | undefined;
      const p = details?.progress;

      if (result.isError) {
        return new Text(theme.fg("error", "✗ Fetch failed — see output above"), 0, 0);
      }

      let text = theme.fg("success", `✓ Fetched ${p?.total ?? "?"}`);
      text += theme.fg("dim", ` listing${(p?.total ?? 0) !== 1 ? "s" : ""}`);
      if (p?.elapsed) text += theme.fg("muted", `  (${p.elapsed.toFixed(0)}s)`);
      return new Text(text, 0, 0);
    },
  });

  // ── Tool: craigslist_display ─────────────────────────────
  pi.registerTool({
    name: "craigslist_display",
    label: "Display Results",
    description:
      "Re-rank existing Craigslist listings and generate an HTML report (opens in browser). " +
      "No network access — runs instantly on already-fetched data. " +
      "Call this after updating scoring rules to see new rankings without re-fetching.",
    promptSnippet: "Re-rank listings and open HTML results in browser",
    promptGuidelines: [
      "Call craigslist_display after every scoring rule change to let the user see updated rankings in their browser.",
      "craigslist_display never fetches new data — it only re-ranks what was already fetched.",
    ],
    parameters: Type.Object({
      config: Type.String({
        description: "Config file path relative to project root (e.g. 'config/my_search.yaml')",
      }),
      no_dedup: Type.Optional(
        Type.Boolean({
          description: "Skip duplicate filtering (useful when re-parsing same data)",
          default: false,
        }),
      ),
    }),

    async execute(_toolCallId, params, signal, onUpdate, _ctx) {
      const args: string[] = ["--config", params.config, "--display"];
      if (params.no_dedup) args.push("--no-dedup");

      onUpdate?.({
        content: [{ type: "text", text: `⚙️  Ranking listings (config: ${params.config})…\n` }],
      });

      const { output, exitCode } = await runPython(args, signal, onUpdate);

      if (exitCode !== 0) {
        throw new Error(`Display failed (exit ${exitCode}):\n${output}`);
      }

      // Try to open the HTML result in the browser
      const htmlPath = extractHtmlPath(output) ?? latestResultHtml();
      if (htmlPath) {
        const absolutePath = resolve(PROJECT_DIR, htmlPath);
        openFile(absolutePath);
      }

      const truncation = truncateTail(output, {
        maxLines: DEFAULT_MAX_LINES,
        maxBytes: DEFAULT_MAX_BYTES,
      });

      return {
        content: [{ type: "text", text: truncation.content }],
        details: { config: params.config, htmlPath, exitCode },
      };
    },
  });

  // ── Command: /cl-new ─────────────────────────────────────
  pi.registerCommand("cl-new", {
    description: "Start a new Craigslist search — guided setup that creates a config and kicks off the workflow",
    handler: async (args, ctx) => {
      await ctx.waitForIdle();

      ctx.ui.notify("Starting new Craigslist search setup…", "info");

      // 1. What are you looking for?
      const item = await ctx.ui.input(
        "What are you looking for?",
        args.trim() || "e.g. 1990s Honda Civic hatchback",
      );
      if (!item) {
        ctx.ui.notify("Cancelled", "warning");
        return;
      }

      // 2. Key criteria / what matters to you?
      const criteria = await ctx.ui.editor(
        "Describe your ideal listing — what matters most? (one idea per line)",
        `- \n- \n- `,
      );

      // 3. Cities
      const citiesInput = await ctx.ui.input(
        "Which cities? (comma-separated)",
        "sfbay, losangeles, seattle, portland",
      );

      // 4. Budget
      const budget = await ctx.ui.input("Max budget? (leave blank to skip)", "");

      // 5. How many listings?
      const limitChoice = await ctx.ui.select("How many listings to fetch initially?", [
        "10 (quick test)",
        "50 (decent sample)",
        "Unlimited (slow!)",
      ]);

      const limitMap: Record<string, string> = {
        "10 (quick test)": "10",
        "50 (decent sample)": "50",
        "Unlimited (slow!)": "unlimited",
      };
      const limit = limitChoice ? limitMap[limitChoice] ?? "50" : "50";

      // Build the kickoff message for the agent
      const lines = [
        `I want to search Craigslist for: **${item}**`,
        "",
        "**My criteria / what I care about:**",
        criteria?.trim() || "(no extra criteria)",
        "",
        `**Cities to search:** ${citiesInput || "sfbay, losangeles"}`,
        budget ? `**Max budget:** $${budget}` : "",
        `**Listings to fetch:** ${limit}`,
        "",
        "Please:",
        "1. Create a well-structured YAML config in `config/` for this search.",
        "   - Choose a short snake_case filename based on what I'm looking for.",
        "   - Write thoughtful scoring rules that reflect my criteria.",
        "   - Add negative points for common red flags (salvage, dealer, needs work, etc.).",
        `2. Call \`craigslist_fetch\` with the new config${limit !== "unlimited" ? ` and limit=${limit}` : ""}.`,
        "3. Call \`craigslist_display\` so I can review the results in my browser.",
        "4. Summarise what you found and ask for feedback on the ranking.",
      ]
        .filter(Boolean)
        .join("\n");

      pi.sendUserMessage(lines);
    },
  });

  // ── Command: /cl-open ────────────────────────────────────
  pi.registerCommand("cl-open", {
    description: "Re-open the most recent Craigslist results HTML in your browser",
    handler: async (_args, ctx) => {
      const html = latestResultHtml();
      if (!html) {
        ctx.ui.notify("No results HTML found in outputs/results/ — run a search first", "warning");
        return;
      }
      openFile(html);
      ctx.ui.notify(`Opened: ${html}`, "info");
    },
  });

  // ── Command: /cl-refetch ─────────────────────────────────
  pi.registerCommand("cl-refetch", {
    description: "Re-fetch listings for a config (clears storage first). Usage: /cl-refetch config/my_search.yaml",
    handler: async (args, ctx) => {
      await ctx.waitForIdle();

      const configPath = args.trim();
      if (!configPath) {
        ctx.ui.notify("Usage: /cl-refetch config/my_search.yaml", "warning");
        return;
      }

      const ok = await ctx.ui.confirm(
        "Re-fetch listings?",
        `This will CLEAR the existing storage for ${configPath} and fetch fresh listings from Craigslist (slow!). Continue?`,
      );
      if (!ok) {
        ctx.ui.notify("Cancelled", "info");
        return;
      }

      pi.sendUserMessage(
        `Please re-fetch listings for \`${configPath}\` — call \`craigslist_fetch\` with config="${configPath}" and clear=true. After fetching, call \`craigslist_display\` and summarise the results.`,
      );
    },
  });
}
