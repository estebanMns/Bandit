/** Qué le falta a una cuenta para empezar a vigilar. Lógica pura, sin pedidos al servidor. */

export type StepId = "local" | "cai" | "camaras" | "listo";

export interface SetupState {
  hasLocal: boolean;
  hasCai: boolean;
  cameraCount: number;
}

export interface Step {
  id: StepId;
  title: string;
  done: boolean;
  optional: boolean;
}

export function steps(state: SetupState): Step[] {
  const ready = state.hasLocal && state.cameraCount > 0;
  return [
    { id: "local", title: "Tu local", done: state.hasLocal, optional: false },
    { id: "cai", title: "WhatsApp del CAI", done: state.hasCai, optional: true },
    { id: "camaras", title: "Tus cámaras", done: state.cameraCount > 0, optional: false },
    { id: "listo", title: "A vigilar", done: ready, optional: false },
  ];
}

/** El primer paso pendiente; si todo está hecho, el último. */
export function firstPending(state: SetupState): StepId {
  return steps(state).find((step) => !step.done)?.id ?? "listo";
}

export function needsSetup(state: SetupState): boolean {
  return !state.hasLocal || state.cameraCount === 0;
}
