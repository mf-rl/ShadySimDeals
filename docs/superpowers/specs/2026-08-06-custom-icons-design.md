# Custom Icons Design

## Scope

Replace reused base-game icons with the eleven normalized project PNGs for the ShadySimDeals app category, sale actions, rabbit-hole queue actions, traits, and moodlets. This is a presentation-only change: transaction behavior, runtime Python, pricing, filtering, routing, durations, transfers, payments, and consequences remain unchanged.

## Resource strategy

Compile each normalized 256×256 RGBA source PNG to a BC3/DST5 image and package it as resource type `0x00B2D882` in `ShadySimDeals.package`. Assign stable instances from the next unused project range:

| Instance | Source | Use |
| --- | --- | --- |
| `0xEAA21FFB1081E01A` | `icons/Phone-Computer-App/app-icon.png` | Shared phone/computer ShadySimDeals category |
| `0xEAA21FFB1081E01B` | `icons/QueueActions/Sell House Member.png` | **Liquidate a Family Asset** pie-menu and queue icon |
| `0xEAA21FFB1081E01C` | `icons/QueueActions/Sell Unborn Nooboo.png` | **Monetize Future Family Growth** pie-menu and queue icon |
| `0xEAA21FFB1081E01D` | `icons/QueueActions/Attend a Definitely Legal Exchange.png` | Household-sale rabbit-hole queue icon |
| `0xEAA21FFB1081E01E` | `icons/QueueActions/Arrange a Pre-order.png` | Unborn-sale rabbit-hole queue icon |
| `0xEAA21FFB1081E01F` | `icons/Traits/Family Asset Liquidator.png` | **Family Asset Liquidator** trait |
| `0xEAA21FFB1081E020` | `icons/Traits/Outsourced by My Own Family.png` | **Outsourced by My Own Family** trait |
| `0xEAA21FFB1081E021` | `icons/Traits/Stork Claim Mysteriously Denied.png` | **Stork Claim Mysteriously Denied** trait |
| `0xEAA21FFB1081E022` | `icons/Moodlets/Quarterly Profits, Fewer Mouths.png` | **Quarterly Profits, Fewer Mouths** moodlet |
| `0xEAA21FFB1081E023` | `icons/Moodlets/Apparently, Love Had a Return Policy.png` | **Apparently, Love Had a Return Policy** moodlet |
| `0xEAA21FFB1081E024` | `icons/Moodlets/The Nursery Has Been Downsized.png` | **The Nursery Has Been Downsized** moodlet |

The builder validates the normalized PNG source artwork, uses the vendored DirectXTex converter to create temporary DXT5 data, rearranges it into Sims 4 DST5 order, and packages it without retaining generated texture files.

## Tuning and SimData references

- The shared `PieMenuCategory` XML and SimData point to the app icon.
- Both phone and computer household-sale interactions use the household action icon for `_icon` and `pie_menu_icon`.
- Both phone and computer unborn-sale interactions use the unborn action icon for `_icon` and `pie_menu_icon`.
- All three household rabbit-hole interactions use the exchange icon for `_icon`.
- All three unborn rabbit-hole interactions use the pre-order icon for `_icon`.
- Each trait XML and generated Trait SimData point to its matching trait icon.
- Each buff XML and generated Buff SimData point to its matching moodlet icon.
- Generated SimData resource keys use DST image type `0x00B2D882`.

No display names, durations, animation factories, categories, tests, or transaction fields change.

## Failure handling

The build fails if the converter or an expected source icon is missing, invalid, or cannot produce valid one-mip DXT5 data. Package tests verify the complete DST5 resource set, DDS headers, dimensions, stable IDs, XML references, SimData instances and types, and interaction icon mappings. A missing or malformed icon therefore fails before installation rather than silently falling back in game.

## Verification

Automated verification covers:

- all eleven DST5 resources appear in `package_resources()` and the built DBPF index;
- packaged resources have 256×256 DDS headers and the `DST5` FourCC;
- every icon reference resolves to one of those packaged resources;
- trait, buff, category, entry-action, and rabbit-hole mappings are exact;
- existing behavioral tests remain unchanged and pass.

Live verification confirms the app category, both sale actions in pie menus and the interaction queue, both rabbit-hole queue actions, all three traits, and all three moodlets display their intended artwork.
