// saga_machine.hpp — the saga lifecycle as a boost::sml state machine.
//
//   RUNNING --StepSucceeded--> RUNNING        (step_index + 1)
//   RUNNING --AllStepsDone [step_index >= N]--> COMPLETED
//   RUNNING --StepFailed--> COMPENSATING
//   COMPENSATING --Compensated--> COMPENSATED
//
// The machine owns no I/O. The orchestrator executes a step (or its compensation), then
// reports the outcome as an event; the machine decides the next status. Postgres holds the
// persisted status and step_index, and `restore()` rebuilds the machine from them, which is
// how a restarted orchestrator resumes a RUNNING saga.

#pragma once

#include <string>
#include <string_view>
#include <vector>

#include <boost/sml.hpp>

namespace cndp::saga {

namespace sml = boost::sml;

struct StepSucceeded {};
struct StepFailed {};
struct AllStepsDone {};
struct Compensated {};

// States are declared as classes so they can be named when restoring.
struct Running;
struct Compensating;
struct Completed;
struct Compensated_;

struct Progress {
    int step_index = 0;  // index of the next step to run == number of completed steps
    int total_steps = 0;
};

struct Lifecycle {
    auto operator()() const {
        using namespace sml;
        auto all_done = [](Progress& p) { return p.step_index >= p.total_steps; };
        auto advance = [](Progress& p) { ++p.step_index; };
        return make_transition_table(
            *state<Running> + event<StepSucceeded> / advance = state<Running>,
            state<Running> + event<AllStepsDone>[all_done] = state<Completed>,
            state<Running> + event<StepFailed> = state<Compensating>,
            state<Compensating> + event<Compensated> = state<Compensated_>);
    }
};

using Machine = sml::sm<Lifecycle>;

inline std::string_view status_of(const Machine& sm) {
    using namespace sml;
    if (sm.is(state<Running>)) return "RUNNING";
    if (sm.is(state<Compensating>)) return "COMPENSATING";
    if (sm.is(state<Completed>)) return "COMPLETED";
    return "COMPENSATED";
}

// Rebuild a machine at a persisted status by replaying the events that lead there from the
// initial RUNNING state (a COMPLETED saga has step_index == total_steps, so AllStepsDone holds).
inline void restore(Machine& sm, std::string_view status) {
    if (status == "COMPENSATING") {
        sm.process_event(StepFailed{});
    } else if (status == "COMPENSATED") {
        sm.process_event(StepFailed{});
        sm.process_event(Compensated{});
    } else if (status == "COMPLETED") {
        sm.process_event(AllStepsDone{});
    }
}

// Completed steps are undone in reverse order: indices step_index-1 .. 0.
inline std::vector<int> compensation_order(int step_index) {
    std::vector<int> order;
    for (int i = step_index - 1; i >= 0; --i) order.push_back(i);
    return order;
}

}  // namespace cndp::saga
