# Third-party materials

## Kenney Shape

[Kenney Shape](https://kenney.itch.io/kenney-shape) is developed by Kenney. The builder uses the application files, resources, icon, and samples from your local Linux download.

The license included with that download restricts sharing the software. Kenney's [free-download announcement](https://kenney.itch.io/kenney-shape/devlog/1708644/kenney-shape-is-now-free-forever-) doesn't include a new open-source or redistribution license. The MIT license here covers the build tools and adapters only. Sharing a modified app would require separate permission from the relevant rights holders.

This project is unofficial and isn't affiliated with Kenney.

## Unity

The builder uses the official Unity 2021.3.45f2 Mac Mono component, supplied separately by Unity. It copies the player, Mono libraries, and bundle resources into the local build. Those files remain subject to [Unity's terms](https://unity.com/legal) and their component notices.

## Mono.Cecil

The patcher uses [Mono.Cecil 0.11.6](https://www.nuget.org/packages/Mono.Cecil/0.11.6), which is [MIT licensed](https://github.com/jbevain/cecil/blob/master/LICENSE.txt). NuGet downloads it when building the patcher.

## Other tools

Python, the .NET SDK, Apple's command-line tools, macOS frameworks, and Rosetta are installed separately under their own terms.
