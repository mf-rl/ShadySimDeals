# Scripted Rabbit-Hole Liability Design

## Problem

The six custom rabbit-hole affordances load `basic_liabilities` entries as strings. During interaction tuning finalization, the game calls `liability.factory` and raises `AttributeError`, so tuning never finishes. Adding the native XML export key does not change this for these XML-only custom resources.

## Approaches

1. **Scripted interaction subclass (selected).** Remove `basic_liabilities` from XML and add the native `HideSimLiability` through a small `SuperInteraction` subclass. This keeps native routing, hiding, return, and rabbit-hole expiration behavior while avoiding unsupported custom liability deserialization.
2. **Generate interaction SimData.** Package schemas for all six interactions so XML variants deserialize like native resources. This adds a fragile binary generator for one field.
3. **Replace the rabbit-hole lifecycle.** Route, hide, time, and restore Sims in custom Python. This duplicates game behavior and creates more rollback risk.

## Architecture

Add one script module containing a `SuperInteraction` subclass. Its queue lifecycle installs one native `HideSimLiability` before delegating to `SuperInteraction`. The liability remains owned and released by the game's interaction lifecycle.

All six private rabbit-hole XML resources reference the subclass and contain no `basic_liabilities` list. Their existing `Spawn_Arrival` constraints, `rabbit_hole_based` durations, participants, and natural exit actions stay unchanged.

## Data Flow

The rabbit-hole service pushes its tuned affordance. The custom interaction is queued, installs the native hide liability, routes to `Spawn_Arrival`, hides the participating Sim or Sims when running, and exits on the rabbit-hole duration. Native liability release restores returning participants. The service expiration callback then applies the sale and payment.

## Error Handling

The subclass delegates queue behavior to the native implementation. If queuing fails, the interaction never runs and the existing rabbit-hole cancellation path remains responsible for aborting the reserved transaction. No custom hiding or restoration state is introduced.

## Testing

- A unit test supplies minimal fake Sims 4 modules, queues the subclass, and verifies exactly one native hide liability is installed before native queue handling.
- Package tests verify all six affordances use the scripted class and omit XML `basic_liabilities`.
- The complete test suite and package build must pass; installed artifacts must match build hashes.
- In-game verification must first confirm tuning loads without `interaction.py:2339`, then exercise household and unborn sales.
