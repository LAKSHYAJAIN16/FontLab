import { applyVariants } from "./apply";
import type {
  AssignedVariant,
  ConfigResponse,
  GoalDefinition,
  MicroTuneInitOptions,
  TrackedEvent,
} from "./types";
import { getOrCreateVisitorId } from "./visitor";

const DEFAULT_ENDPOINT = "https://edge.microtune.dev";

class MicroTuneClient {
  private projectId: string | null = null;
  private endpoint = DEFAULT_ENDPOINT;
  private visitorId: string | null = null;
  private assignedVariants: AssignedVariant[] = [];
  private goals: GoalDefinition[] = [];
  private ready: Promise<void> | null = null;

  init(options: MicroTuneInitOptions): void {
    this.projectId = options.project;
    this.endpoint = options.endpoint ?? DEFAULT_ENDPOINT;
    this.visitorId = getOrCreateVisitorId();
    this.ready = this.loadConfig();
  }

  goal(definition: GoalDefinition): void {
    this.goals.push(definition);
    document.addEventListener(definition.event, () => this.trackGoal(definition.name));
  }

  private async loadConfig(): Promise<void> {
    if (!this.projectId || !this.visitorId) return;

    const url = `${this.endpoint}/config?project=${encodeURIComponent(this.projectId)}&visitor=${encodeURIComponent(this.visitorId)}`;
    const response = await fetch(url, { credentials: "omit" });
    if (!response.ok) return;

    const config: ConfigResponse = await response.json();
    this.assignedVariants = config.variants;

    applyVariants(this.assignedVariants);
    for (const variant of this.assignedVariants) this.trackImpression(variant);
  }

  private trackImpression(variant: AssignedVariant): void {
    this.sendEvent({
      type: "impression",
      experimentId: variant.experimentId,
      variantId: variant.variantId,
    });
  }

  private trackGoal(goalName: string): void {
    this.sendEvent({ type: "goal", goalName });
  }

  private sendEvent(partial: Omit<TrackedEvent, "projectId" | "visitorId" | "timestamp">): void {
    if (!this.projectId || !this.visitorId) return;

    const event: TrackedEvent = {
      ...partial,
      projectId: this.projectId,
      visitorId: this.visitorId,
      timestamp: Date.now(),
    };

    const url = `${this.endpoint}/events`;
    const body = JSON.stringify(event);

    if (navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: "application/json" }));
    } else {
      fetch(url, { method: "POST", body, keepalive: true, headers: { "Content-Type": "application/json" } });
    }
  }
}

export const MicroTune = new MicroTuneClient();
export type { MicroTuneInitOptions, GoalDefinition, AssignedVariant, ConfigResponse, TrackedEvent };
