import { describe, it, expect, vi } from "vitest";
import { EventBus } from "../src/events.js";
import type { EngineEvent } from "../src/events.js";

function sampleEvent(): EngineEvent {
  return { type: "session:completed", sessionId: "s1" };
}

describe("EventBus", () => {
  it("delivers an emitted event to a subscribed listener", () => {
    const bus = new EventBus();
    const listener = vi.fn();
    bus.on(listener);
    const event = sampleEvent();
    bus.emit(event);
    expect(listener).toHaveBeenCalledWith(event);
  });

  it("delivers to multiple listeners", () => {
    const bus = new EventBus();
    const a = vi.fn();
    const b = vi.fn();
    bus.on(a);
    bus.on(b);
    bus.emit(sampleEvent());
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
  });

  it("unsubscribe (the function returned by on()) stops further delivery", () => {
    const bus = new EventBus();
    const listener = vi.fn();
    const unsubscribe = bus.on(listener);
    unsubscribe();
    bus.emit(sampleEvent());
    expect(listener).not.toHaveBeenCalled();
  });

  it("emitting with no listeners does not throw", () => {
    const bus = new EventBus();
    expect(() => bus.emit(sampleEvent())).not.toThrow();
  });

  it("a listener removing itself mid-emit does not affect other listeners in the same emit call", () => {
    const bus = new EventBus();
    const b = vi.fn();
    const holder: { unsubscribeA?: () => void } = {};
    const a = vi.fn(() => holder.unsubscribeA?.());
    holder.unsubscribeA = bus.on(a);
    bus.on(b);
    bus.emit(sampleEvent());
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
  });
});
