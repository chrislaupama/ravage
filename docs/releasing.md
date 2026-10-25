# Releasing RAVAGE

Every release on GitHub gets standalone packages for Linux, Windows and macOS, built by `.github/workflows/release.yml`.

## Making a release

Push a version tag:

```
git tag v0.1.0
git push origin v0.1.0
```

Or, on GitHub, draft a new release with a new `v...` tag and publish it. Either way the workflow builds the three packages, tests each one on its own operating system, and attaches them to the release with a `SHA256SUMS.txt` file. For a pushed tag it creates the release first, with notes generated from the merged pull requests. A tag with a hyphen, such as `v0.2.0-beta.1`, is marked as a pre-release.

To try the packages without releasing, run the workflow by hand from the Actions tab (Run workflow) and download them from the run's artifacts. Pull requests that change the packaging run it too.

## What's in a package

| Package | Contents |
|---|---|
| `ravage-<version>-linux-x86_64.tar.gz` | `ravage`, `ravage-sv` and `base/`. Needs glibc 2.35 or later (Ubuntu 22.04, Debian 12, Fedora 36, SteamOS 3 or newer), with SDL2 and OpenGL from the system. |
| `ravage-<version>-windows-x86_64.zip` | `ravage.exe`, `ravage-sv.exe` and `base/`. Windows 10 or later; needs no extra DLLs. |
| `ravage-<version>-macos-universal.zip` | `RAVAGE.app` (Apple silicon and Intel, macOS 11 or later) with the server and game data inside, and a `ravage-sv` link to the server. |

![What a Linux package holds, and its package test](images/release-package-contents.png)

Each one also holds:

- `README.txt`: how to run the game and server, and the credits.
- `LICENSE.txt`: the GPL, which covers the engine. The README links the source for the release's tag.
- `licenses/`: LibreQuake's BSD license and contributor list, which must travel with its models and sounds (see [licensing.md](licensing.md#librequake)), and the license of every library built into that package (zlib, libpng and FreeType on Windows; SDL2, libpng, FreeType and epoll-shim on macOS).

Packages never contain Quake assets, the QuakeC compiler or the map tools. `tests/package.sh` checks each package for the license files and for Quake files, and checks that the server loads `duel_graybox` and the client finds the package's game data when started from another folder. It also runs under `ctest` with a Linux package built from `build/`.

The programs look for `base/` in the working directory first, then next to the executable (inside a macOS app, in `Contents/Resources`). So a package runs from a shortcut, from Finder or from any terminal folder, and `-basedir` still overrides both.

![The Linux package, unpacked and started from another folder, in the arena](images/release-linux-package.png)

## macOS signing and notarization

With the repository secrets below, the workflow signs the app with your Developer ID, notarizes it with Apple and staples the ticket, so it opens like any downloaded Mac app. Without them it falls back to an ad-hoc signature: macOS then blocks the app on first launch until the player chooses Open Anyway in System Settings > Privacy & Security, and the README says so.

Add them under the repository's Settings > Secrets and variables > Actions:

| Secret | What it is |
|---|---|
| `MACOS_CERTIFICATE` | Your **Developer ID Application** certificate and its private key, exported from Keychain Access as a `.p12` file and base64-encoded: `base64 -i ravage.p12 \| pbcopy` |
| `MACOS_CERTIFICATE_PASSWORD` | The password you gave the `.p12` export |
| `APPLE_API_KEY` | An App Store Connect API key for notarization: the contents of the `.p8` file |
| `APPLE_API_KEY_ID` | That key's Key ID |
| `APPLE_API_ISSUER` | The Issuer ID shown above the keys list |

To get them:

1. **Certificate.** In Xcode, Settings > Accounts > your team > Manage Certificates, add a *Developer ID Application* certificate (or create one at developer.apple.com > Certificates; only the account holder can). In Keychain Access, find "Developer ID Application: …" under My Certificates, right-click > Export, save as `.p12` with a password.
2. **API key.** At appstoreconnect.apple.com > Users and Access > Integrations > App Store Connect API, generate a key with the *Developer* role and download the `.p8` (it can be downloaded only once).

The next run of the workflow signs and notarizes; its `macos` job checks the result with `spctl`, as Gatekeeper would. Pull requests that change the packaging get signed builds too, since the secrets are available to branches in this repository.

## Building a package locally

After building the programs and the game data (see [building.md](building.md)):

```
tools/package-release.sh linux-x86_64 v0.1.0 build/bin build/game dist
tests/package.sh dist/ravage-v0.1.0-linux-x86_64
```

Windows packages need the dependency prefix as a sixth argument (`deps/win64`) for its license files. macOS packages must be built on a Mac, with the libraries from `tools/build-macos-deps.sh`; the workflow's `macos` job shows the CMake options.
