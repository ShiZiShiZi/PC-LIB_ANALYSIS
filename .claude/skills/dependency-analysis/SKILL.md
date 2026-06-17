---
name: dependency-analysis
description: Identify and explain a third-party library's dependencies across ecosystems (Python, C/C++, Java, JS/TS) by reading manifest and build files, then reasoning about what each dependency is and why it's used. Distinguishes runtime vs dev/test/build deps. Use for dimension 6 of PC library analysis. Model reasoning over manifests, not a fixed parser.
---

# Dependency analysis (model-driven)

Read the dependency manifests and build files, then produce a clean list with
scope and purpose. A rigid parser misses bundled headers, transitive build
deps, and ecosystem-specific quirks — reason about them.

## Manifests by ecosystem
- **Python**: `requirements*.txt`, `pyproject.toml` (`[project].dependencies`,
  `[project.optional-dependencies]`, poetry/PDM tables), `setup.py`
  (`install_requires`/`extras_require`), `setup.cfg`, `Pipfile`, `environment.yml`.
- **C/C++**: `CMakeLists.txt` / `*.cmake` (`find_package`, `target_link_libraries`,
  `FetchContent`, `ExternalProject`), `vcpkg.json`, `conanfile.txt`/`.py`,
  `Makefile` (`-l` link flags, `pkg-config`), git submodules (`.gitmodules`),
  vendored `third_party/`/`extern/` trees.
- **Java**: `pom.xml` (`<dependencies>`, distinguish `<scope>`), `build.gradle`(`.kts`)
  (`implementation`/`api`/`testImplementation`/`compileOnly`), `ivy.xml`.
- **JS/TS**: `package.json` (`dependencies` / `devDependencies` /
  `peerDependencies` / `optionalDependencies`), workspace/monorepo manifests.

## How to analyze
1. Find every manifest (record their paths in `manifests`).
2. Extract each declared dependency with its **ecosystem**, **scope**
   (runtime / dev / test / optional / build / peer) and **version constraint**.
3. For notable runtime deps, add a short **purpose** ("HTTP transport",
   "JSON parsing", "test framework") inferred from name + how it's imported/used.
4. Separate the project's **own** name and standard-library/system packages from
   real third-party deps. C/C++ `find_package(Threads)`, `PkgConfig`, the
   project itself, etc. are build plumbing — mark scope `build` or drop.
5. Note **vendored** dependencies (copied into the tree) and **git submodules**
   separately — they won't appear in a package manifest.

## Output (fills report `dependencies`)
```json
{
  "count": 5,
  "manifests": ["pyproject.toml", "requirements-dev.txt"],
  "by_ecosystem": {"python": ["urllib3", "certifi"]},
  "dependencies": [
    {"name": "urllib3", "ecosystem": "python", "scope": "runtime",
     "version": ">=1.21.1", "purpose": "low-level HTTP connection pooling"}
  ],
  "notes": "Also vendors 'chardet' under src/; pytest is dev-only."
}
```

## Rules
- Prefer runtime deps in the headline `count`; keep dev/test/build but scoped.
- Don't list transitive deps unless lockfiles are the only source and the user
  needs them — say so in `notes` if you do.
