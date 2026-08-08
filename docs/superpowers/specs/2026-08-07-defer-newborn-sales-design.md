# Defer Newborn Sales Design

## Goal

Stop offering newborns in the household-member sale picker while preserving
working infant-through-elder and unborn sales.

## Design

Reject Sims whose normalized age is `baby` in
`eligible_household_member_ids()`, before shared picker filtering. This is the
single boundary that supplies household-sale picker rows, so newborns cannot
start a transaction. Infant and older eligibility remains unchanged.

Keep the existing newborn adapter and packaged pickup tuning dormant. Removing
that code would enlarge this safety change and risk disturbing infant carry or
shared rabbit-hole behavior. It can be removed separately if newborn support is
permanently abandoned.

## Verification

- A runtime regression proves an on-lot newborn is excluded.
- The same test proves an eligible infant remains included.
- Existing filtering, adapter, transaction, build, and packaging tests remain
  green.
- Maintained documentation states that newborn sales are unsupported/deferred
  and removes newborn live-test instructions.

## Scope

No feature flag, notification, pricing change, picker change, rabbit-hole
change, dependency, or unrelated refactor is included.
