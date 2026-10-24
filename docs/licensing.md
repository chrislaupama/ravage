# Licensing

## Engine code

RAVAGE ENGINE is derived from GPL-licensed Quake technology (FTEQW, and selected code from Ironwail and QuakeSpasm). The engine is therefore distributed under the GNU General Public License, version 2 or later. The full text is in [LICENSE](../LICENSE).

When importing upstream code:

- Keep every existing copyright and license notice.
- Record where each import came from (repository, commit) in the commit message.
- Review the license of every dependency before adding it, and note any that are not GPLv2-compatible.

## Game content

Maps, models, textures, audio, artwork and branding must be original or properly licensed for RAVAGE. The GPL on the Quake engine source does not grant any right to Quake's commercial assets, so none of them may be committed or distributed.

### Using your own Quake install for development

Developers who legally own Quake may point a local build at their own copy (for example its `id1/` folder) to use as a reference or temporary placeholder while original content is made. The engine can read `.pak` files, `.mdl` models and `.wad` textures for this reason. Those files stay on the developer's machine: `.gitignore` excludes `id1/` and `pak*.pak`, and nothing from them may be committed, packaged, uploaded to CI or shipped. RAVAGE must always run standalone, using only its own redistributable placeholder content.

GPL-licensed Quake *code*, such as the QuakeWorld QuakeC game logic, is different. It can be reused or adapted, provided its copyright notices are kept and the result stays under the GPL.

The license for original RAVAGE content, tooling and online services has not been decided yet and will be documented here.

## Naming

"RAVAGE" is a working name and has not been cleared for trademark or store use. Other games using the name exist. Clearance must happen before any public branding, domains or store listings.
