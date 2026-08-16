export interface MicroTuneInitOptions {
  /** Public project identifier, e.g. "project_123". */
  project: string;
  /** Override the edge endpoint base URL (defaults to the CDN edge). */
  endpoint?: string;
}

export interface GoalDefinition {
  /** Human-readable goal name, e.g. "signup". */
  name: string;
  /** DOM CustomEvent name, or a native event dispatched on `document`, that marks completion. */
  event: string;
}

/** A single CSS property override applied to an element for one experiment arm. */
export type VariantPatch = Record<string, string>;

export interface AssignedVariant {
  experimentId: string;
  /** CSS selector for the element this variant applies to. */
  selector: string;
  variantId: string;
  patch: VariantPatch;
}

export interface ConfigResponse {
  projectId: string;
  visitorId: string;
  variants: AssignedVariant[];
}

export interface TrackedEvent {
  projectId: string;
  visitorId: string;
  type: "impression" | "goal";
  experimentId?: string;
  variantId?: string;
  goalName?: string;
  timestamp: number;
}
