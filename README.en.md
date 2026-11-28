# Material2Video

[中文](README.md)

**Turn articles, data, and media into editable short videos.**

Use a storyboard to organize the content and code to create the visuals. Keep the media, subtitles, and finished video together in a project that can run on its own.

![A frame from Solar System Journey showing Saturn's golden rings](docs/site/assets/hero.jpg)

**[Watch the examples][video-gallery]** · **[Make your first video](#make-your-first-video-in-three-minutes)** · **[Explore the source](ARCHITECTURE.md)**

## Examples

| Work | Type | Length | What to watch for |
| --- | --- | ---: | --- |
| [40 Years of Compound Interest](examples/data-evolution/compound-after-20/README.md) | Data evolution | 38.7 s | Interest bars grow from zero, then form two towers that explain the 6.73× difference between the two 20-year periods. [Video page][video-compound-after-20] |
| [Global Top 10 by Market Cap](examples/data-evolution/global-market-cap-race-portrait/README.md) | Data evolution | 107.13 s | Follow rankings from 2000 to 2026 and see how the lead changes in a portrait layout with room for platform overlays. [Video page][video-global-market-cap-race-portrait] |
| [Solar System Journey](examples/spatial-3d/solar-system-journey/README.md) | Spatial 3D | 120 s | Travel through 15 stops, from the Earth–Moon relationship to a reveal of Saturn’s rings and the scale of the outer Solar System. [Video page][video-solar-system-journey] |

The gallery includes silent excerpts and preview frames. Each example README includes its storyboard, design notes, and recovery steps. [View the gallery locally](docs/site/README.md)
All three examples can be restored and exported as standalone projects. [Example index and reproduction steps](examples/README.md)

## Make your first video in three minutes

[Follow the tested three-second title video walkthrough](README.md#三分钟做出第一条视频) for the shared PowerShell and bash commands, exact font prerequisites, and measured Windows 11 timings. Linux and macOS were not verified in this run. [Copy a ten-second portrait video task for a coding assistant](docs/agent-quickstart.md).

## How it works

Start with articles, data, and media. The storyboard sets scene timing and points to the scene source.
That code controls layout, camera, lighting, and motion. Capture records the rendered visuals frame by frame.
The project’s `SceneFilm` composition assembles the clips, transitions, and subtitles before audio mixing and export.
Each project runs with its own source, dependency locks, and asset recovery scripts.
[Architecture and module responsibilities](ARCHITECTURE.md)

## Current capabilities

Five video types share a standalone project foundation. Each project adopts the components and media it needs.

- `text-motion` generates text and graphics in code for typography and motion.
- `data-evolution` visualizes changes in structured data.
- `spatial-3d` renders 3D models and spaces.

Create visuals in code or edit recorded media. Map routes and situational storytelling are available as techniques.
Projects support clip previews and full exports, synthesized narration, project-local sound recipes, and bilingual subtitles with an adaptive halo.

## Documentation

The [technical reference index](docs/reference/README.md) groups the detailed guides by topic.

- [Project model and storyboard](docs/reference/project-model.md) covers versions, source references, dependency locks, and asset recovery.
- [Voice and subtitles](docs/reference/voice-and-subtitles.md) covers voice backends, reference voices, bilingual subtitles, and adaptive halos.
- [Native web samples and media review](docs/reference/sample-and-review.md) covers capture, preview, review, and delivery.
- [Materials, attribution, and project storage](docs/reference/materials.md) covers sourcing records, adoption policy, caches, and paths.

The [production skill](.agents/skills/material2video/SKILL.md) describes the production stages and their requirements.
See the [OpenSpec specifications](openspec/specs/) for current behavior and the [project plan](docs/PROJECT_PLAN.md) for future work.

## Contributing and licensing

Feedback on production or reproduction issues is welcome, along with improvements to the docs, examples, and tools.
See the [contributing guide](CONTRIBUTING.md) and [v0.1.0 release notes with English summary](docs/release-notes/v0.1.0.md#英文摘要).
See [AGENTS.md](AGENTS.md) for the repository’s verification and commit conventions.

Original code, documentation, example source, and original scripts use the [MIT License](LICENSE).
Remotion is licensed separately. Other materials with licensing notices follow their stated terms.
See the [third-party notices](THIRD_PARTY_NOTICES.md) for dependencies, fonts, models, and example media.

[video-gallery]: https://haoaoqikf.github.io/material2video/
[video-compound-after-20]: https://haoaoqikf.github.io/material2video/work-compound.html
[video-global-market-cap-race-portrait]: https://haoaoqikf.github.io/material2video/work-market-cap.html
[video-solar-system-journey]: https://haoaoqikf.github.io/material2video/work-solar-system.html
