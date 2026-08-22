# Operating surface concepts

Swingle's dispatch surface has two sides. Each side is a small, fixed hierarchy, not a
flat list of interchangeable knobs.

## Requirements side: what kind of work this is

```
Lane (2 values, fixed)
├── implement
│   ├── reader contract
│   └── implementer contract
└── review
    ├── task-reviewer contract
    └── design-reviewer contract
```

**Lane** is one of exactly two values: `implement` or `review`. It is the only key
`providers_by_lane` in [config.md](config.md) accepts. There is no third lane, and a lane
name is never invented to fit a task description; a task that doesn't obviously read as
"implement" or "review" still resolves to one of the two.

**Role**, expressed as a contract file under `contracts/`, is the more specific choice
within a lane: `reader` or `implementer` under the `implement` lane, `task-reviewer` or
`design-reviewer` under the `review` lane. The contract determines the brief the delegated
CLI receives. Lane is derived from which contract the task calls for, not chosen
independently of it.

## Execution side: how the work actually runs

```
Provider (7 values, fixed: providers/ directory listing)
└── Tier (3 values: cheapest, standard, most-capable)
    └── Model + Effort (one joined choice)
```

**Provider** is which installed CLI runs the job: the live listing of `providers/`, per
[config.md](config.md).

**Tier** is the advisory task-intent label (`cheapest`, `standard`, `most-capable`
documented in [model-tiering.md](model-tiering.md)) used to resolve a preferred model when
none is explicit.

**Model and effort are one joined choice, not two independent dials.** A resolved
preference is "this model, at this effort," decided together, because a model's practical
capability and cost depend on both at once. Swingle's `model_preferences` schema stores
only a model name; effort is never a config field. Effort is set at dispatch time,
directly on the provider CLI invocation.

**How a provider's CLI actually accepts that joined choice is provider-specific and not
fixed across providers or CLI versions.** Some expose effort as a flag fully separate from
the model flag; some accept effort folded into the model identifier itself as an
alternative to a separate flag; some route it through a generic config-override mechanism
instead of a dedicated flag; some may not expose CLI-level effort control at all. Do not
assume one provider's pattern applies to another, and do not carry a pattern forward from
an earlier session or an older provider version. Inspect the target provider's current
`--help` before combining model and effort for a dispatch, the same help-first grounding
`swingle-delegate` already applies before every dispatch.
