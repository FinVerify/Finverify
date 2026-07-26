import type { ExtractedClaim } from "../types.js";
import type { VerifierPlugin } from "./types.js";

export class PluginRegistry {
  private readonly plugins = new Map<string, VerifierPlugin>();

  register(plugin: VerifierPlugin): void {
    if (this.plugins.has(plugin.id)) {
      throw new Error(`A plugin with id "${plugin.id}" is already registered.`);
    }
    this.plugins.set(plugin.id, plugin);
  }

  unregister(pluginId: string): void {
    this.plugins.delete(pluginId);
  }

  get(pluginId: string): VerifierPlugin | undefined {
    return this.plugins.get(pluginId);
  }

  list(): VerifierPlugin[] {
    return Array.from(this.plugins.values());
  }

  /** Runs every registered plugin (or a specific subset by id) over
   *  `text` and merges the results. Defensively re-stamps `domain` on
   *  each claim to the owning plugin's id — a plugin author forgetting
   *  to set it correctly shouldn't be able to cause claims to be
   *  misattributed to the wrong domain. */
  detectAll(text: string, pluginIds?: string[]): ExtractedClaim[] {
    const targets = pluginIds ? pluginIds.map((id) => this.plugins.get(id)).filter((p): p is VerifierPlugin => !!p) : this.list();

    const results: ExtractedClaim[] = [];
    for (const plugin of targets) {
      const claims = plugin.detectClaims(text);
      for (const claim of claims) {
        results.push({ ...claim, domain: plugin.id });
      }
    }
    return results;
  }
}
