import random
import math
from copy import deepcopy
from common.equivalence import equivalence
from common.TimedWord import TimedWord
from common.hypothesis import OTATran
from common.TimeInterval import guard_split
from testing.random_testing import test_generation_1, test_generation_2, test_generation_4, get_random_delay


class NFA(object):
    def __init__(self, states, init_state, actions, trans, sink_state, final_states):
        self.states = states
        self.init_state = init_state
        self.actions = actions
        self.trans = trans
        self.sink_state = sink_state
        self.final_states = final_states  # timed中为接受状态集合，state中为更改接受性的最终状态


# 基于变异的测试主函数
def mutation_testing(hypothesisOTA, upper_guard, state_num, pre_ctx, system, generate, selection, operator):
    equivalent = True
    ctx = None

    # parameter setting - generation
    pstart = 0.4
    pstop = 0.05
    pvalid = 0.8
    pretry = 0.9
    linfix = math.ceil(state_num / 2)
    # max_steps = min(int(2 * state_num), int(2 * len(hypothesisOTA.states)))
    max_steps = int(2 * state_num)
    test_num = int(state_num * len(hypothesisOTA.actions) * upper_guard * 30)

    # parameter setting - mutation
    duration = system.get_minimal_duration(upper_guard)  # It can also be set by the user.
    nacc = 8
    k = 1

    # test cases generation
    tests = []
    # tests_random = []
    for i in range(test_num):
        if generate == 'random':
            tests.append(test_generation_1(hypothesisOTA, upper_guard, state_num))
        elif generate == 'A&T':
            tests.append(test_generation_2(hypothesisOTA, pretry, pstop, max_steps, linfix, upper_guard))
        elif generate == 'heuristic':
            tests.append(test_generation_4(hypothesisOTA, pstart, pstop, pvalid, max_steps, upper_guard, pre_ctx))
        else:
            raise Exception('no such generate option')
        # tests_random.append(tests[i].time_words)


    if operator == 'both':
        tested = []  # test cases tested
        # step1: timed变异
        timed_tests = mutation_timed(hypothesisOTA, duration, upper_guard, tests, selection)
        if len(timed_tests) > 0:
            print('number of timed tests', len(timed_tests))
            equivalent, ctx = test_execution(hypothesisOTA, system, timed_tests)
            tested = timed_tests

        # step2: if no ctx, location-mutation
        if equivalent:
            state_tests = mutation_state(hypothesisOTA, state_num, nacc, k, tests, selection)
            if len(state_tests) > 0:
                state_tests = remove_tested(state_tests, tested)
                print('number of state tests', len(state_tests))
                equivalent, ctx = test_execution(hypothesisOTA, system, state_tests)
                tested += state_tests
    elif operator == 'timed':
        timed_tests = mutation_timed(hypothesisOTA, duration, upper_guard, tests, selection)
        if len(timed_tests) > 0:
            print('number of timed tests', len(timed_tests))
            equivalent, ctx = test_execution(hypothesisOTA, system, timed_tests)
    elif operator == 'split':
        state_tests = mutation_state(hypothesisOTA, state_num, nacc, k, tests, selection)
        if len(state_tests) > 0:
            print('number of state tests', len(state_tests))
            equivalent, ctx = test_execution(hypothesisOTA, system, state_tests)
    else:
        raise Exception('no such operator option')

    return equivalent, ctx


def model_based_mutation_testing(hypothesisOTA, upper_guard, state_num, pre_ctx, system):
    equivalent = True
    ctx = None

    # parameter setting - mutation
    duration = system.get_minimal_duration(upper_guard)  # It can also be set by the user.
    nacc = 8
    k = 1
    tests = []
    # step1: timed变异
    equivalent, ctx, timed_tests = mutation_timed_inreal(system, hypothesisOTA, duration, upper_guard, tests)

    tested = timed_tests
    if equivalent:
        equivalent, ctx, state_tests = mutation_state_inreal(system, hypothesisOTA, state_num, nacc, k, upper_guard, tests)
        tested += state_tests

    return equivalent, ctx


# timed mutation
def mutation_timed(hypothesis, duration, upper_guard, tests, selection):
    Tsel = []
    # mutant generation
    mutants = timed_mutation_generation(hypothesis, duration, upper_guard)  # 这里的mutants是trans信息
    print('number of timed_mutations', len(mutants))
    # generate NFA
    muts_NFA = timed_NFA_generation(mutants, hypothesis)
    print('number of timed NFA trans', len(muts_NFA.trans))
    # mutation analysis
    print('Starting mutation analysis...')
    tran_dict = get_tran_dict(muts_NFA)
    tests_valid = []
    C = []
    C_tests = []
    for test in tests:
        C_test, C = timed_mutation_analysis(muts_NFA, hypothesis, test, C, tran_dict)
        if C_test:
            tests_valid.append(test)
            C_tests.append(C_test)
    if C:
        coverage = float(len(C)) / float(len(mutants))
        print("timed mutation coverage:", coverage)
    # test case selection
    if C_tests:
        if selection == 'score':
            Tsel = test_selection(tests_valid, C, C_tests)
        elif selection == 'greedy':
            Tsel = test_selection_old(tests_valid, C, C_tests)
        else:
            raise Exception('no such selection option')
        print("T/Tsel:", len(tests_valid), len(Tsel))
    return Tsel


# timed mutation generation/operator
def timed_mutation_generation(hypothesis, duration, upper_guard):
    mutations = []
    mut_num = 0
    for tran in hypothesis.trans:
        if tran.source == hypothesis.sink_state and tran.target == hypothesis.sink_state:
            continue
        trans = split_tran_guard(tran, duration, upper_guard)
        for state in hypothesis.states:
            for temp_tran in trans:
                if temp_tran.target == state and temp_tran.reset == tran.reset:
                    continue
                temp = deepcopy(temp_tran)
                temp.target = state
                temp.tran_id = 'mut' + str(mut_num)
                mut_num += 1
                mutations.append(temp)
    return mutations

# timed mutation generation/operator
def mutation_timed_inreal(system, hypothesis, duration, upper_guard, tests):
    mut_num = 0

    equ = True
    ctx = None

    for tran in hypothesis.trans:
        if tran.source == hypothesis.sink_state and tran.target == hypothesis.sink_state:
            continue
        trans = []
        for guard in tran.guards:
            temp_guards = guard_split(guard, duration, upper_guard)
            if not temp_guards:
                trans.append(OTATran('', tran.source, tran.action, [guard], tran.reset, tran.target))
            for temp_guard in temp_guards:
                trans.append(OTATran('', tran.source, tran.action, [temp_guard], tran.reset, tran.target))
        for temp_tran in trans:
            for state in hypothesis.states:
                temp = deepcopy(temp_tran)
                temp.reset = not temp.reset
                temp.target = state
                temp.tran_id = 'mut' + str(mut_num)
                Mutant = deepcopy(hypothesis)
                for t in Mutant.trans:
                    if t.tran_id == tran.tran_id:
                        Mutant.trans.remove(t)
                        break
                mut_trans = []
                for tt in trans:
                    mut_trans.append(tt)
                mut_trans.remove(temp_tran)
                Mutant.trans.append(temp)
                Mutant.trans.extend(mut_trans)
                Mutant.simple_transitions()

                correct_flag, test = equivalence(hypothesis, Mutant, upper_guard)
                if not correct_flag and test:
                    test.append(TimedWord(random.choice(hypothesis.actions), get_random_delay(upper_guard)))
                    tests.append(test)
                    equ, ctx = test_execution(hypothesis, system, [test])
                    if not equ:
                        return equ, ctx, tests
                mut_num += 1

                if temp_tran.target == state:
                    continue
                temp = deepcopy(temp_tran)
                temp.target = state
                temp.tran_id = 'mut' + str(mut_num)
                Mutant = deepcopy(hypothesis)
                for t in Mutant.trans:
                    if t.tran_id == tran.tran_id:
                        Mutant.trans.remove(t)
                        break
                mut_trans = []
                for tt in trans:
                    mut_trans.append(tt)
                mut_trans.remove(temp_tran)
                Mutant.trans.append(temp)
                Mutant.trans.extend(mut_trans)
                Mutant.simple_transitions()

                correct_flag, test = equivalence(hypothesis, Mutant, upper_guard)
                if not correct_flag and test:
                    test.append(TimedWord(random.choice(hypothesis.actions), get_random_delay(upper_guard)))
                    tests.append(test)
                    equ, ctx = test_execution(hypothesis, system, [test])
                    if not equ:
                        return equ, ctx, tests
                mut_num += 1
    return equ, ctx, tests



# generate timed_mutant_NFA structure
def timed_NFA_generation(mutants, hypothesis):
    hypothesis = deepcopy(hypothesis)
    trans = hypothesis.trans
    trans.extend(mutants)
    return NFA(hypothesis.states, hypothesis.init_state, hypothesis.actions, trans, hypothesis.sink_state, hypothesis.accept_states)


# timed mutation analysis
def timed_mutation_analysis(muts_NFA, hypothesis, test_tuple, C, tran_dict):
    C_test = []
    test = test_tuple.time_words

    hyp_tran_dict = get_tran_dict(hypothesis)
    now_time = 0
    now_state = hypothesis.init_state
    test_result = []

    for t in test:
        temp_time = t.time + now_time
        new_LTW = TimedWord(t.action, temp_time)
        for tran in hyp_tran_dict[now_state]:
            if tran.is_passing_tran(new_LTW):
                now_state = tran.target
                if tran.reset:
                    now_time = 0
                else:
                    now_time = temp_time
                if now_state in hypothesis.accept_states:
                    test_result.append(1)
                elif now_state == hypothesis.sink_state:
                    test_result.append(-1)
                else:
                    test_result.append(0)

    def tree_create(state, preTime, test_index, mut_tran):
        if test_index >= len(test):
            return True
        cur_time = test[test_index].time + preTime
        cur_LTW = TimedWord(test[test_index].action, cur_time)

        if mut_tran:
            if state == mut_tran.source and mut_tran.is_passing_tran(cur_LTW):
                cur_trans = [mut_tran]
            else:
                cur_trans = hyp_tran_dict[state]
            for cur_tran in cur_trans:
                if cur_tran.is_passing_tran(cur_LTW):
                    if cur_tran.reset:
                        tempTime = 0
                    else:
                        tempTime = cur_time
                    if cur_tran.target in muts_NFA.final_states:
                        state_flag = 1
                    elif cur_tran.target == muts_NFA.sink_state:
                        state_flag = -1
                    else:
                        state_flag = 0

                    if state_flag != test_result[test_index]:
                        if mut_tran.tran_id not in C_test:
                            C_test.append(mut_tran.tran_id)
                        if mut_tran.tran_id not in C:
                            C.append(mut_tran.tran_id)
                        return True
                    else:
                        tree_create(cur_tran.target, tempTime, test_index + 1, mut_tran)
        else:
            cur_trans = tran_dict[state]
            for cur_tran in cur_trans:
                if cur_tran.is_passing_tran(cur_LTW):
                    if cur_tran.reset:
                        tempTime = 0
                    else:
                        tempTime = cur_time
                    if cur_tran.target in muts_NFA.final_states:
                        state_flag = 1
                    elif cur_tran.target == muts_NFA.sink_state:
                        state_flag = -1
                    else:
                        state_flag = 0
                    if isinstance(cur_tran.tran_id, str):
                        mut_tran = cur_tran
                        if state_flag != test_result[test_index]:
                            if mut_tran.tran_id not in C_test:
                                C_test.append(mut_tran.tran_id)
                            if mut_tran.tran_id not in C:
                                C.append(mut_tran.tran_id)
                            return True
                        else:
                            tree_create(cur_tran.target, tempTime, test_index + 1, mut_tran)
                    else:
                        tree_create(cur_tran.target, tempTime, test_index + 1, mut_tran)

    tree_create(muts_NFA.init_state, 0, 0, None)
    return C_test, C


# timed_mutation_analysis_old
def timed_mutation_analysis_old(muts_NFA, hypothesis, test_tuple, C, tran_dict):
    C_test = []
    test = test_tuple.time_words

    # 获取test在hypothesis里的结果，用于与muts区分
    hyp_tran_dict = get_tran_dict(hypothesis)
    now_time = 0
    now_state = hypothesis.init_state
    test_result = []
    for t in test:
        temp_time = t.time + now_time
        new_LTW = TimedWord(t.action, temp_time)
        for tran in hyp_tran_dict[now_state]:
            if tran.is_passing_tran(new_LTW):
                now_state = tran.target
                if tran.reset:
                    now_time = 0
                else:
                    now_time = temp_time
                if now_state in hypothesis.accept_states:
                    test_result.append(1)
                elif now_state == hypothesis.sink_state:
                    test_result.append(-1)
                else:
                    test_result.append(0)

    def tree_create(state, preTime, test_index, mut_tran):
        if test_index >= len(test):
            return True
        cur_time = test[test_index].time + preTime
        cur_LTW = TimedWord(test[test_index].action, cur_time)

        if mut_tran:
            if state == mut_tran.source and mut_tran.is_passing_tran(cur_LTW):
                if mut_tran.reset:
                    tempTime = 0
                else:
                    tempTime = cur_time
                if mut_tran.target in muts_NFA.final_states:
                    state_flag = 1
                elif mut_tran.target == muts_NFA.sink_state:
                    state_flag = -1
                else:
                    state_flag = 0
                if state_flag != test_result[test_index]:
                    if mut_tran.tran_id not in C_test:
                        C_test.append(mut_tran.tran_id)
                    if mut_tran.tran_id not in C:
                        C.append(mut_tran.tran_id)
                    return True
                tree_create(mut_tran.target, tempTime, test_index + 1, mut_tran)
                return True
            else:
                cur_trans = hyp_tran_dict[state]
        else:
            cur_trans = tran_dict[state]

        for cur_tran in cur_trans:
            if cur_tran.is_passing_tran(cur_LTW):
                if cur_tran.reset:
                    tempTime = 0
                else:
                    tempTime = cur_time
                if cur_tran.target in muts_NFA.final_states:
                    state_flag = 1
                elif cur_tran.target == muts_NFA.sink_state:
                    state_flag = -1
                else:
                    state_flag = 0

                if isinstance(cur_tran.tran_id, str):
                    mut_tran = cur_tran

                if mut_tran:
                    if state_flag != test_result[test_index]:
                        if mut_tran.tran_id not in C_test:
                            C_test.append(mut_tran.tran_id)
                        if mut_tran.tran_id not in C:
                            C.append(mut_tran.tran_id)
                        return True
                tree_create(cur_tran.target, tempTime, test_index + 1, mut_tran)

    tree_create(muts_NFA.init_state, 0, 0, None)
    return C_test, C


# split_state mutation
def mutation_state(hypothesis, state_num, nacc, k, tests, selection):
    Tsel = []
    # 生成变异体
    mutants = split_state_mutation_generation(hypothesis, nacc, k, state_num)
    print('number of split_state_mutations', len(mutants))
    # 生成NFA
    muts_NFA = state_NFA_generation(mutants, hypothesis)
    print('number of state NFA trans', len(muts_NFA.trans))
    # 变异分析
    print('Starting mutation analysis...')
    tran_dict = get_tran_dict(muts_NFA)
    tests_valid = []
    C = []
    C_tests = []
    for test in tests:
        C_test, C = state_mutation_analysis(muts_NFA, test, C, tran_dict)
        if C_test:
            tests_valid.append(test)
            C_tests.append(C_test)
    if C:
        coverage = float(len(C)) / float(len(mutants))
        print("state mutation coverage:", coverage)
    # test case selection
    if C_tests:
        if selection == 'score':
            Tsel = test_selection(tests_valid, C, C_tests)
        elif selection == 'greedy':
            Tsel = test_selection_old(tests_valid, C, C_tests)
        else:
            raise Exception('no such selection option')
        print("T/Tsel:", len(tests_valid), len(Tsel))
    return Tsel

def mutation_state_inreal(system, hypothesis, state_num, nacc, k, upper_guard, tests):
    #Tsel = []
    mut_num = 0
    equ = True
    ctx=None

    for state in hypothesis.states:
        if state == hypothesis.sink_state:
            continue
        set_accq = get_all_acc(hypothesis, state, state_num)
        if len(set_accq) < 2:
            continue
        elif nacc >= len(set_accq):
            subset_accq = set_accq
        else:
            subset_accq = random.sample(set_accq, nacc)
        for s1 in subset_accq:
            for s2 in subset_accq:
                if s1 == s2:
                    continue
                else:
                    if not s1:
                        continue
                    else:
                        suffix = arg_maxs(s1, s2)
                        prefix = s1[0:len(s1) - len(suffix)]
                        temp_state = s1[-1].target
                        if len(prefix) == 0:
                            p_tran = OTATran('', hypothesis.init_state, None, None, True, hypothesis.init_state)
                        else:
                            p_tran = prefix[len(prefix) - 1]
                    mutants = []
                    trans_list = k_step_trans(hypothesis, temp_state, k)
                    for distSeq in trans_list:
                        Mutant = deepcopy(hypothesis)
                        new_s = len(Mutant.states)
                        Mutant.states.append(new_s)
                        for t in Mutant.trans:
                            if p_tran.equal_trans(t):
                                t.target = new_s
                                break
                        mut_tran = [p_tran] + suffix + distSeq
                        for i in range(1, len(mut_tran)):
                            pre_s = new_s
                            for tran in hypothesis.trans:
                                if tran.source == mut_tran[i].source and not tran.equal_trans(mut_tran[i]):
                                    Mutant.trans.append(OTATran(str(len(Mutant.trans)), pre_s, tran.action, tran.guards, tran.reset, tran.target))
                            if i < len(mut_tran)-1:
                                new_s = len(Mutant.states)
                                Mutant.states.append(new_s)
                                Mutant.trans.append(OTATran(str(len(Mutant.trans)), pre_s, mut_tran[i].action, mut_tran[i].guards, mut_tran[i].reset, new_s))
                            else:
                                Mutant.trans.append(OTATran(str(len(Mutant.trans)), pre_s, mut_tran[i].action, mut_tran[i].guards, mut_tran[i].reset, mut_tran[i].target))
                                if not mut_tran[i].source in hypothesis.accept_states:
                                    Mutant.accept_states.append(pre_s)
                        correct_flag, test = equivalence(hypothesis, Mutant, upper_guard)
                        if not correct_flag and test:
                            test.append(TimedWord(random.choice(hypothesis.actions), get_random_delay(upper_guard)))
                            tests.append(test)
                            equ, ctx = test_execution(hypothesis, system, [test])
                            if not equ:
                                return equ, ctx, tests
                        mut_num += 1
    return equ, ctx, tests


# split-state mutation generation
def split_state_mutation_generation(hypothesis, nacc, k, state_num):
    temp_mutations = []
    for state in hypothesis.states:
        if state == hypothesis.sink_state:
            continue
        set_accq = get_all_acc(hypothesis, state, state_num)
        if len(set_accq) < 2:
            continue
        elif nacc >= len(set_accq):
            subset_accq = set_accq
        else:
            subset_accq = random.sample(set_accq, nacc)
        for s1 in subset_accq:
            for s2 in subset_accq:
                if s1 == s2:
                    continue
                else:
                    muts = split_state_operator(s1, s2, k, hypothesis)
                    if muts is not None:
                        temp_mutations.extend(muts)
    return temp_mutations


# generate state_mutant_NFA structure
def state_NFA_generation(mutations, hypothesis):
    hypothesis = deepcopy(hypothesis)
    states = hypothesis.states
    init_state = hypothesis.init_state
    actions = hypothesis.actions
    trans = hypothesis.trans
    sink_state = hypothesis.sink_state
    final_states = []
    mId = 0
    for mutation in mutations:
        count = 0
        source_state = mutation[0].source
        target_state = None
        for tran in mutation:
            tran = deepcopy(tran)
            target_state = str(mId) + '_' + str(count)
            tran.source = source_state
            tran.target = target_state
            trans.append(tran)
            states.append(target_state)
            count += 1
            source_state = target_state
        mId += 1
        final_states.append(target_state)
    return NFA(states, init_state, actions, trans, sink_state, final_states)


# state_mutation_analysis
def state_mutation_analysis(muts_NFA, test_tuple, C, tran_dict):
    test = test_tuple.time_words
    C_test = []

    def tree_create(state, preTime, test_index):
        if test_index >= len(test):
            return True
        cur_time = test[test_index].time + preTime
        new_LTW = TimedWord(test[test_index].action, cur_time)
        if state not in tran_dict.keys():
            return True
        cur_trans = tran_dict[state]
        for tran in cur_trans:
            if tran.is_passing_tran(new_LTW):
                if tran.reset:
                    tempTime = 0
                else:
                    tempTime = cur_time
                if tran.target in muts_NFA.final_states:
                    mId = tran.target.split('_')[0]
                    if mId not in C_test:
                        C_test.append(mId)
                    if mId not in C:
                        C.append(mId)
                if tran.target == muts_NFA.sink_state:
                    continue
                tree_create(tran.target, tempTime, test_index + 1)

    tree_create(muts_NFA.init_state, 0, 0)
    return C_test, C


# test-case selection
def test_selection(Tests, C, C_tests):
    Tsel = []
    c = deepcopy(C)  # all mutations
    tests = deepcopy(Tests)  # tests
    cset = deepcopy(C_tests)  # tests 对应的 cover mutation set
    # 获取 mut_num 和 test_len 的最小值和最大值，用于归一化
    max_mutWeight = 0
    max_lenWeight = 0
    max_tranWeight = 0
    max_stateWeight = 0
    max_timeWeight = 0
    min_mutWeight = float('inf')
    min_lenWeight = float('inf')
    min_tranWeight = float('inf')
    min_stateWeight = float('inf')
    min_timeWeight = float('inf')
    for i in range(len(tests)):
        mut_num = len(cset[i])
        if mut_num > max_mutWeight:
            max_mutWeight = mut_num
        if mut_num < min_mutWeight:
            min_mutWeight = mut_num
        test_length = tests[i].length
        if test_length > max_lenWeight:
            max_lenWeight = test_length
        if test_length < min_lenWeight:
            min_lenWeight = test_length
        if tests[i].tran_weight < min_tranWeight:
            min_tranWeight = tests[i].tran_weight
        if tests[i].tran_weight > max_tranWeight:
            max_tranWeight = tests[i].tran_weight
        if tests[i].state_weight < min_stateWeight:
            min_stateWeight = tests[i].state_weight
        if tests[i].state_weight > max_stateWeight:
            max_stateWeight = tests[i].state_weight
        if tests[i].time_weight < min_timeWeight:
            min_timeWeight = tests[i].time_weight
        if tests[i].time_weight > max_timeWeight:
            max_timeWeight = tests[i].time_weight
    # calculate weight and normalization
    weight(tests, cset, max_mutWeight, min_mutWeight, max_lenWeight, min_lenWeight, max_tranWeight, min_tranWeight, max_stateWeight, min_stateWeight, max_timeWeight, min_timeWeight)

    cover_set = {}
    for mut_item in c:
        cover_set[mut_item] = []
        for j in range(len(tests)):
            if mut_item in cset[j]:
                cover_set[mut_item].append((j, tests[j], tests[j].weight))
        cover_set[mut_item] = sorted(cover_set[mut_item], key=lambda x: x[2], reverse=True)
    cover_set = sorted(cover_set.items(), key=lambda d: len(d[1]))

    for ctest in cover_set:
        union = list(set(Tsel).intersection(ctest[1]))
        if not union:
            Tsel.append(ctest[1][0])

    test_suite = []
    for item in Tsel:
        test_suite.append(item[1].time_words)
    return test_suite


def test_selection_old(Tests, C, C_tests):
    Tsel = []
    c = deepcopy(C)  # all mutations
    tests = deepcopy(Tests)  # tests
    cset = deepcopy(C_tests)  # tests - cover mutation set
    pre_set = []
    while c:
        cur_index = 0
        cur_max = []
        for i in range(len(cset)):
            cset[i] = list(set(cset[i]).difference(set(pre_set)))
            if len(cur_max) < len(cset[i]):
                cur_max = cset[i]
                cur_index = i
        if cur_max:
            Tsel.append(tests[cur_index])
            pre_set = cur_max
        else:
            break
    test_suite = []
    for item in Tsel:
        test_suite.append(item.time_words)
    return test_suite


# test_case execution
def test_execution(hypothesis, system, tests):
    flag = True
    ctx = []
    for test in tests:
        DRTWs, value = hypothesis.test_DTWs(test)
        realDRTWs, realValue = system.test_DTWs(test)
        if realValue != value:
            flag = False
            ctx = test
            return flag, ctx
    return flag, ctx


# --------------------------------- auxiliary function --------------------------------

# delete cur_tests
def remove_tested(tests, cur_tests):
    for test in cur_tests:
        if test in tests:
            tests.remove(test)
    return tests


# group
def get_tran_dict(muts_NFA):
    tran_dict = {}
    for tran in muts_NFA.trans:
        if tran.source in tran_dict.keys():
            tran_dict[tran.source].append(tran)
        else:
            tran_dict[tran.source] = [tran]
    return tran_dict


# split_tran_guard
def split_tran_guard(tran, region_num, upper_guard):
    trans = []
    for guard in tran.guards:
        temp_guards = guard_split(guard, region_num, upper_guard)
        if not temp_guards:
            trans.append(OTATran('', tran.source, tran.action, [guard], tran.reset, tran.target))
            trans.append(OTATran('', tran.source, tran.action, [guard], not tran.reset, tran.target))
        for temp_guard in temp_guards:
            trans.append(OTATran('', tran.source, tran.action, [temp_guard], tran.reset, tran.target))
            trans.append(OTATran('', tran.source, tran.action, [temp_guard], not tran.reset, tran.target))
    return trans


# split-state operator
def split_state_operator(s1, s2, k, hypothesis):
    if not s1:
        suffix = []
        p_tran = OTATran('', hypothesis.init_state, None, None, True, hypothesis.init_state)
        temp_state = hypothesis.init_state
    else:
        suffix = arg_maxs(s1, s2)
        prefix = s1[0:len(s1) - len(suffix)]
        temp_state = s1[-1].target
        if len(prefix) == 0:
            p_tran = OTATran('', hypothesis.init_state, None, None, True, hypothesis.init_state)
        else:
            p_tran = prefix[len(prefix) - 1]
    mutants = []
    trans_list = k_step_trans(hypothesis, temp_state, k)
    for distSeq in trans_list:
        mut_tran = [p_tran] + suffix + distSeq
        mutants.append(mut_tran)
    return mutants


# get mutated access seq leading to a single state
def get_all_acc(hypothesis, state, state_num):
    paths = []
    max_path_length = min(int(len(hypothesis.states) * 1.5), state_num * 1.5)

    if state == hypothesis.init_state:
        paths.append([])

    def get_next_tran(sn, path):
        if len(path) > max_path_length or sn == hypothesis.sink_state:
            return True
        if sn == state and path:
            if path not in paths:
                paths.append(path)
        for tran in hypothesis.trans:
            if tran.source == sn:
                if len(path) > 0 and tran == path[-1]:
                    continue
                get_next_tran(tran.target, deepcopy(path) + [tran])

    get_next_tran(hypothesis.init_state, [])
    return paths


# find common suffix
def arg_maxs(s1, s2):
    ts = []
    if len(s1) < len(s2):
        min_test = s1
    else:
        min_test = s2
    for i in range(len(min_test)):
        if not s1[-1 - i].tran_id == s2[-1 - i].tran_id:
            break
        ts = min_test[(len(min_test) - 1 - i):]
    return ts


# find all paths after qs
def k_step_trans(hypothesis, q, k):
    trans_list = []

    def recursion(cur_state, paths):
        if len(paths) == k:
            if paths not in trans_list:
                trans_list.append(paths)
            return True
        for tran in hypothesis.trans:
            if tran.source == cur_state:
                if len(paths) > 0 and paths[-1] == tran:
                    continue
                recursion(tran.target, deepcopy(paths) + [tran])

    recursion(q, [])
    return trans_list


# weight function
def weight(tests, cset, max_mutWeight, min_mutWeight, max_lenWeight, min_lenWeight, max_tranWeight, min_tranWeight, max_stateWeight, min_stateWeight, max_timeWeight, min_timeWeight):
    a = 0.6
    b = 0.4
    c = 0.2
    d = 0.0
    e = 0.4

    mut_range = max_mutWeight - min_mutWeight
    len_range = max_lenWeight - min_lenWeight
    tran_range = max_tranWeight - min_tranWeight
    state_range = max_stateWeight - min_stateWeight
    time_range = max_timeWeight - min_timeWeight
    for i in range(len(tests)):
        if mut_range == 0:
            tests[i].mut_weight = 0
        else:
            tests[i].mut_weight = (len(cset[i]) - min_mutWeight) / mut_range
        if len_range == 0:
            tests[i].len_weight = 0
        else:
            tests[i].len_weight = 1 - (tests[i].length - min_lenWeight) / len_range
        if tran_range == 0:
            tests[i].tran_weight = 0
        else:
            tests[i].tran_weight = (tests[i].tran_weight - min_tranWeight) / tran_range
        if state_range == 0:
            tests[i].state_weight = 0
        else:
            tests[i].state_weight = (tests[i].state_weight - min_stateWeight) / state_range

        if time_range == 0:
            tests[i].time_weight = 0
        else:
            tests[i].time_weight = 1 - (tests[i].time_weight - min_timeWeight) / time_range

        tests[i].weight = a * tests[i].mut_weight + b * tests[i].len_weight + c * tests[i].tran_weight + d * tests[i].state_weight + e * tests[i].time_weight
