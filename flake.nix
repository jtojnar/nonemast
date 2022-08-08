{
  description = "Tool for reviewing GNOME update Nixpkgs PRs";

  inputs = {
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };

    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, flake-compat, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            self.overlay
          ];
        };
      in {
        devShells = {
          default = pkgs.mkShell {
            nativeBuildInputs = pkgs.nonemast.nativeBuildInputs ++ (with pkgs; [
              python3.pkgs.black
            ]);

            inherit (pkgs.nonemast) buildInputs propagatedBuildInputs;
          };
        };

        packages = rec {
          nonemast = pkgs.nonemast;
          default = nonemast;
        };

        apps = {
          default = utils.lib.mkApp {
            drv = self.packages.${system}.nonemast;
          };
        };
      }
  ) // {
    overlay = final: prev: {
      nonemast =
        final.python3.pkgs.buildPythonApplication rec {
          pname = "nonemast";
          version = "0.1.0";

          format = "other";

          src = final.nix-gitignore.gitignoreSource [] ./.;

          nativeBuildInputs = with final; [
            meson
            ninja
            pkg-config
            gobject-introspection
            desktop-file-utils
            gtk4 # for gtk4-update-icon-cache
            wrapGAppsHook4
          ];

          buildInputs = with final; [
            gtk4
            libgit2-glib
            (libadwaita.overrideAttrs (attrs: rec {
              version = "1.2.alpha";

              src = fetchFromGitLab {
                domain = "gitlab.gnome.org";
                owner = "GNOME";
                repo = "libadwaita";
                rev = version;
                hash = "sha256-JMxUeIOUPp9k5pImQqWLVkQ2GHaKvopvg6ol9pvA+Bk=";
              };
            }))
          ];

          propagatedBuildInputs = with final.python3.pkgs; [
            pygobject3
            linkify-it-py
          ];

          # Breaks some setup hooks.
          strictDeps = false;
        };
    };
  };
}
