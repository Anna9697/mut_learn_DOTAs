from copy import deepcopy
from common.system import build_canonicalOTA
from common.equivalence import equivalence
from testing.random_testing import test_generation_0


def validate(learned_system, system):
    upper_guard = system.max_time_value()
    new_system = build_canonicalOTA(deepcopy(system))
    correct_flag, ctx = equivalence(learned_system, new_system, upper_guard)
    if correct_flag:
        passingRate = 1
    else:
        failNum = 0
        testNum = 50000
        for i in range(testNum):
            sample = test_generation_0(learned_system.actions, upper_guard, len(learned_system.states))
            system_res, real_value = new_system.test_DTWs(sample)
            hypothesis_res, value = learned_system.test_DTWs(sample)
            if real_value != value:
                failNum += 1
        passingRate = (testNum - failNum) / testNum
    return correct_flag, passingRate
