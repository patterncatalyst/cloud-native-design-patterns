# Example 17: Saga State & Compensation (C++)

Saga orchestrator on Drogon, with the saga lifecycle as a **boost::sml** state machine and
**libpq** (direct, parameterised statements) for the persisted state.

## Lifecycle

```
RUNNING --StepSucceeded--> RUNNING            (step_index + 1)
RUNNING --AllStepsDone [step_index >= N]--> COMPLETED
RUNNING --StepFailed--> COMPENSATING
COMPENSATING --Compensated--> COMPENSATED
```

`src/saga_machine.hpp` holds the machine and has no I/O. The orchestrator in `src/main.cpp`
runs a step (or its compensation), reports the outcome as an event, and writes the status the
machine lands in. Every step is its own transaction (`SELECT ... FOR UPDATE`), so a crash
leaves the saga `RUNNING` at the last committed `step_index`. On startup the orchestrator
rebuilds each unfinished saga's machine from Postgres (`restore()`) and continues it.
Compensation runs completed steps in reverse (`release_stock`, then `refund_payment`).

## Contract

`POST /sagas`, `GET /sagas/{id}`, `GET /sagas/{id}/log`, `GET /healthz`; steps
`charge_payment`, `reserve_stock`, `book_shipping`; `"fail_shipping": true` in the request body
makes the last step fail. Same as the other languages.

## Build

C++23, GCC 15 (`gcc-toolset-15` on `ubi10/ubi:10.2`), CMake 4.4.4, Ninja 1.13.2, Conan 2.33.0
(Drogon 1.9.13, libpq 17.11, sml 1.2.0). `tests/saga_test.cpp` checks the transitions and the
compensation order under CTest during the image build. The runtime image is `ubi10/ubi-minimal`
with libstdc++ linked statically.

```bash
docker compose up --build   # from examples/17-sagas/cpp
```
