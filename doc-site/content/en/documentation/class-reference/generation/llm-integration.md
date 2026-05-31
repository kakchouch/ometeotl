---
title: "LLMGenerationAdapter / LLMRefinementResult"
---

Source:
- [src/ometeotl_core/generation/llm_integration.py](https://github.com/kakchouch/ometeotl/blob/main/src/ometeotl_core/generation/llm_integration.py)

__

Local role:
Provider-agnostic bridge that converts a `GenerationContext` into a prompt, calls an external text generator, parses the response, and returns a refined `GenerationContext`.

Big-picture role:
Optional pre-refinement step in the hybrid generation workflow (F-20). Keeps LLM usage opt-in and auditable — the pipeline does not call the adapter automatically.

Parameters and fields (`LLMGenerationAdapter`):
- `text_generator: Callable[[str], str]` — any callable that takes a prompt and returns a text response
- `response_parser: Callable[[str], Mapping[str, Any]] | None` — optional custom parser; defaults to `json.loads`-based mapping extraction

Methods (`LLMGenerationAdapter`):
- `render_prompt(context, *, prompt_template=None) -> str` — serializes context to a deterministic JSON payload embedded in the prompt template
- `refine(context, *, prompt_template=None) -> LLMRefinementResult` — renders prompt, calls the generator, parses, merges via `copy_with`; falls back to original context on failure

Parameters and fields (`LLMRefinementResult`, frozen dataclass):
- `refined_context: GenerationContext` — context after LLM-suggested refinements, or original on fallback
- `raw_response: str` — raw text returned by the generator
- `used_fallback: bool` — `True` if parsing or merging failed
- `diagnostics: list[str]` — human-readable messages describing what happened

Notes:
- The adapter is stateless and side-effect-free beyond the external generator call.
- Fallback behavior ensures the pipeline is never blocked by an LLM error.
- Callers must chain the adapter explicitly; the pipeline does not invoke it automatically.

See also:
- [GenerationContext](/ometeotl/documentation/class-reference/generation/generation-context/)
- [Pipeline](/ometeotl/documentation/class-reference/generation/pipeline/)

## Provider integration pattern

```python
def my_llm(prompt: str) -> str:
    return call_openai_or_anthropic(prompt)

adapter = LLMGenerationAdapter(text_generator=my_llm)
refinement = adapter.refine(context)

if not refinement.used_fallback:
    context = refinement.refined_context

result = pipeline.generate(context)
```
