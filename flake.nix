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
              python3.pkgs.mypy
              python3.pkgs.pygobject-stubs
            ]);

            inherit (pkgs.nonemast) buildInputs propagatedBuildInputs checkInputs;
          };
        };

        packages = rec {
          nonemast = pkgs.nonemast;
          python3 = pkgs.python3;
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
      python3 = prev.python3.override (prevArgs: {
        packageOverrides =
          let
            emptyOverlay = final: prev: {};
            ourOverlay = ppFinal: ppPrev: {
              pygobject-stubs = ppFinal.callPackage ./pygobject-stubs.nix {};
            };
          in
          prev.lib.composeExtensions
            prevArgs.packageOverrides or emptyOverlay
            ourOverlay;
      });

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
            libadwaita
          ];

          propagatedBuildInputs = with final.python3.pkgs; [
            pygobject3
            linkify-it-py
          ];

          checkInputs = with final.python3.pkgs; [
            final.git
            pytest
          ];

          doCheck = true;

          checkPhase = ''
            runHook preCheck

            # buildPythonPackage has doCheck enable installCheckPhase but ninja registers regular checkPhase
            # so we need to run it manually.
            meson test --print-errorlogs

            runHook postCheck
          '';

          # Breaks some setup hooks.
          strictDeps = false;
        };
    };
  };
}
