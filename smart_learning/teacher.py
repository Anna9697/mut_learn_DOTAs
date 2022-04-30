import copy
from common.TimedWord import TimedWord, LRTW_to_LTW, DRTW_to_LRTW
from testing.random_testing import random_testing_1, random_testing_2, random_testing_3, random_testing_4
from testing.mutation_testing import mutation_testing, model_based_mutation_testing


def TQs(LTWs, system):
    LRTWs, value = system.test_LTWs(LTWs)
    return LRTWs, value


def EQs(hypothesisOTA, system, pre_ctx, exp, generate, selection, operator):
    upper_guard = system.max_time_value()  # It can also be set by the user.
    state_num = len(system.states)  # non-essential

    # # 测试1 - 完全随机测试
    # equivalent, ctx = random_testing_1(hypothesisOTA, upper_guard, state_num, system)

    # # 测试2 - 随机测试（用于结合mutation testing）
    # equivalent, ctx = random_testing_2(hypothesisOTA, upper_guard, state_num, system)

    # # 测试3 - 随机游走测试
    # equivalent, ctx = random_testing_3(hypothesisOTA, upper_guard, state_num, system)

    # # 测试4 - 改进的随机测试（用于结合mutation testing）
    # equivalent, ctx = random_testing_4(hypothesisOTA, upper_guard, state_num, pre_ctx, system)

    # 测试5 - mutation-based-testing
    if exp == 'mutation_new':
        equivalent, ctx = mutation_testing(hypothesisOTA, upper_guard, state_num, pre_ctx, system, generate, selection, operator)
    elif exp == 'mutant_checking':
        equivalent, ctx = model_based_mutation_testing(hypothesisOTA, upper_guard, state_num, pre_ctx, system)
    elif exp == 'heuristic_random':
        equivalent, ctx = random_testing_4(hypothesisOTA, upper_guard, state_num, pre_ctx, system)
    else:
        raise Exception('no such exp option')

    # 测试6 - model-based-mutation testing
    # equivalent, ctx = model_based_mutation_testing(hypothesisOTA, upper_guard, state_num, pre_ctx, system)



    if ctx is not None:
        ctx = minimize_counterexample(hypothesisOTA, system, ctx)

    system.eq_num += 1
    return equivalent, ctx


# --------------------------------- auxiliary function ---------------------------------

# 最小化反例
def minimize_counterexample(hypothesis, system, ctx):
    ### 最小化反例的长度
    mini_ctx = []
    for dtw in ctx:
        mini_ctx.append(dtw)
        if test_execution(hypothesis, system, mini_ctx):
            break
    ### 局部最小化反例的时间
    # Find sequence of reset information
    reset = []
    DRTWs, value = system.test_DTWs(mini_ctx)
    for drtw in DRTWs:
        reset.append(drtw.reset)
    # ctx to LTWs
    LTWs = LRTW_to_LTW(DRTW_to_LRTW(DRTWs))
    # start minimize
    for i in range(len(LTWs)):
        while True:
            if i == 0 or reset[i - 1]:
                can_reduce = (LTWs[i].time > 0)
            else:
                can_reduce = (LTWs[i].time > LTWs[i - 1].time)
            if not can_reduce:
                break
            LTWs_temp = copy.deepcopy(LTWs)
            LTWs_temp[i] = TimedWord(LTWs[i].action, one_lower(LTWs[i].time))
            if not test_execution(hypothesis, system, LTW_to_DTW(LTWs_temp, reset)):
                break
            LTWs = copy.deepcopy(LTWs_temp)
    return LTW_to_DTW(LTWs, reset)


def one_lower(x):
    if x - int(x) == 0.5:
        return int(x)
    else:
        return x - 0.5


def LTW_to_DTW(LTWs, reset):
    DTWs = []
    for j in range(len(LTWs)):
        if j == 0 or reset[j - 1]:
            DTWs.append(TimedWord(LTWs[j].action, LTWs[j].time))
        else:
            DTWs.append(TimedWord(LTWs[j].action, LTWs[j].time - LTWs[j - 1].time))
    return DTWs


# 测试执行
def test_execution(hypothesis, system, sample):
    system_res, real_value = system.test_DTWs(sample)
    hypothesis_res, value = hypothesis.test_DTWs(sample)
    return real_value != value
