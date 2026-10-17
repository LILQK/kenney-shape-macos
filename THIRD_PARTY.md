# Third-party materials

## Kenney Shape

Kenney Shape is developed by Kenney. Obtain it from [the official download page](https://kenney.itch.io/kenney-shape). Its application code, resources, icon, sample projects, and original libraries are not included in this tools repository. A local build copies them from the distribution selected by the user and modifies one local assembly for compatibility.

The original distribution's license restricts sharing the software. The [announcement making the application free to download](https://kenney.itch.io/kenney-shape/devlog/1708644/kenney-shape-is-now-free-forever-) does not itself provide an open-source or redistribution license. The tools license does not replace the application's terms or establish permission to distribute a modified build. Obtain the relevant rights holders' authorization before publishing an application bundle or original materials.

The name is used to identify the application these tools support. This project is unofficial and does not imply endorsement by Kenney.

## Unity and Mono runtime components

The user separately obtains the official Unity 2021.3.45f2 Mac Mono support component from Unity. No Unity player, runtime library, framework, or template resource is stored in this repository. The builder copies selected files locally after validating their identities. Applicable [Unity terms](https://unity.com/legal) and component notices remain in force.

## Mono.Cecil

The assembly patcher declares [Mono.Cecil 0.11.6](https://www.nuget.org/packages/Mono.Cecil/0.11.6) as a NuGet dependency. Mono.Cecil is distributed under its [MIT license](https://github.com/jbevain/cecil/blob/master/LICENSE.txt). The source release contains the package declaration and lockfile; NuGet obtains the library during a local build.

## Build prerequisites

The .NET SDK, Python, Apple's command-line tools, macOS frameworks, and Rosetta are provided separately under their own terms. This repository does not redistribute them or automatically install system components.

## Repository license scope

The repository's MIT License covers its original build scripts, patcher logic, native adapter implementation, tests, and documentation. It grants no rights over separately obtained software, trademarks, or generated application bundles.
