# Shady Trait Presentation Design

## Goal

Make all three sale-consequence traits display their existing localized names
and descriptions, and identify them with the shared native origin label
**Shady Attribute**.

## Presentation

Keep the approved trait content unchanged:

1. **Family Asset Liquidator** — applied to a successful seller.
2. **Outsourced by My Own Family** — applied to a sold household member.
3. **Stork Claim Mysteriously Denied** — applied to a non-selling pregnant Sim
   whose unborn Nooboo was sold.

Add one localized origin label: **Shady Attribute**. Each trait remains
permanent, visible, non-CAS-selectable, and outside personality-trait slots.

## Technical Design

Update the generated Trait SimData to match the current client Trait schema.
Populate its `display_name`, `trait_description`, and
`trait_origin_description` fields. Keep both ordinary and gender-neutral
display-name fields in the XML tuning, where the gender-neutral field belongs.
Keep the trait type as the native gameplay type.

Do not copy WickedWhims' custom trait-type value or depend on WickedWhims. Its
Wicked Attribute presentation is mod-specific and could create enum or version
conflicts. The native origin label provides the requested grouping language
without another mod dependency or a custom UI.

No transaction, rabbit-hole, payment, pregnancy, trait-assignment, or moodlet
behavior changes.

## Verification

Automated tests must verify that all three Trait SimData resources contain:

- their existing localized display-name and description keys;
- both ordinary and gender-neutral display-name fields in XML tuning;
- the shared Shady Attribute origin-description key;
- the native gameplay trait type;
- the correct Trait SimData resource keys and current schema.

The complete test suite and package build must pass. Live verification must
confirm that seller, sold, and lost-unborn traits show their names,
descriptions, and Shady Attribute label without UI exceptions.
