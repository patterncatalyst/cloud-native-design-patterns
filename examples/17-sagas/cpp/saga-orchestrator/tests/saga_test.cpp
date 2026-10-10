// Unit tests for the saga lifecycle (boost::sml) and the compensation order.
#include <cstdio>

#include "saga_machine.hpp"

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    std::printf("%s %s\n", ok ? "ok  " : "FAIL", what);
    if (!ok) ++failures;
}
}  // namespace

int main() {
    using namespace cndp::saga;

    {  // happy path: three steps, then completion
        Progress p{0, 3};
        Machine sm{p};
        check(status_of(sm) == "RUNNING", "starts RUNNING");
        sm.process_event(AllStepsDone{});
        check(status_of(sm) == "RUNNING", "AllStepsDone ignored before the last step");
        for (int i = 0; i < 3; ++i) sm.process_event(StepSucceeded{});
        check(p.step_index == 3, "step_index advanced to 3");
        sm.process_event(AllStepsDone{});
        check(status_of(sm) == "COMPLETED", "COMPLETED after the last step");
        sm.process_event(StepFailed{});
        check(status_of(sm) == "COMPLETED", "COMPLETED is terminal");
    }
    {  // failure on step 3: compensate steps 1 and 2 in reverse
        Progress p{0, 3};
        Machine sm{p};
        sm.process_event(StepSucceeded{});
        sm.process_event(StepSucceeded{});
        sm.process_event(StepFailed{});
        check(status_of(sm) == "COMPENSATING", "StepFailed -> COMPENSATING");
        auto order = compensation_order(p.step_index);
        check(order.size() == 2 && order[0] == 1 && order[1] == 0, "compensation runs 1 then 0");
        sm.process_event(Compensated{});
        check(status_of(sm) == "COMPENSATED", "COMPENSATED at the end");
    }
    {  // resume: restored RUNNING saga at step 1 finishes
        Progress p{1, 3};
        Machine sm{p};
        restore(sm, "RUNNING");
        sm.process_event(StepSucceeded{});
        sm.process_event(StepSucceeded{});
        sm.process_event(AllStepsDone{});
        check(status_of(sm) == "COMPLETED", "restored RUNNING saga completes");
    }
    {  // resume mid-compensation
        Progress p{2, 3};
        Machine sm{p};
        restore(sm, "COMPENSATING");
        check(status_of(sm) == "COMPENSATING", "restored COMPENSATING");
        sm.process_event(Compensated{});
        check(status_of(sm) == "COMPENSATED", "restored COMPENSATING finishes");
    }
    {  // an unknown status is rejected, not treated as RUNNING
        Progress p{1, 3};
        Machine sm{p};
        check(!restore(sm, "PAUSED"), "unknown status rejected");
        check(!restore(sm, ""), "empty status rejected");
        check(!restore(sm, "running"), "status match is exact");
        check(restore(sm, "RUNNING") && restore(sm, "COMPLETED"), "known statuses accepted");
    }
    check(compensation_order(0).empty(), "nothing to compensate before step 1");
    return failures == 0 ? 0 : 1;
}
