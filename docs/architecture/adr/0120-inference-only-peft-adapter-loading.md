<!--
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright 2026-present Gabby Contributors.
-->

# ADR 0120: Model adapter loading boundary

- Status: superseded
- Date: 2026-10-03

The previously accepted model adapter loading capability has been removed. Gabby does not train
models, modify model weights, or load model adapters. A host configures an agent's requested
character through instructions and optional context; these guide model output but do not guarantee
behavior. Runtime policies enforce tool access and execution boundaries. See
[ADR 0121](0121-runtime-specialization-boundary.md).
