# random testing method
import random
import copy
import queue
import math
from common.TimedWord import TimedWord, TestInfo


# random testing method 1 - pure random
def random_testing_1(hypothesis, upper_guard, state_num, system):
    test_num = int(len(hypothesis.states) * len(hypothesis.actions) * upper_guard * 10)

    ctx = None
    for i in range(test_num):
        test = test_generation_1(hypothesis.actions, upper_guard, state_num)
        flag = test_execution(hypothesis, system, test)
        if flag:
            ctx = test
            break
    if ctx is not None:
        return False, ctx
    return True, ctx


# test-case generation 0（random testing method 1）
def test_generation_0(actions, upper_guard, state_num):
    test = []
    length = random.randint(1, state_num * 2)
    for i in range(length):
        action = actions[random.randint(0, len(actions) - 1)]
        time = get_random_delay(upper_guard)
        temp = TimedWord(action, time)
        test.append(temp)
    return test

# test-case generation（random testing method 1）
def test_generation_1(hypothesis, upper_guard, state_num):
    test = TestInfo([])
    tran_coverage = []
    state_coverage = []
    state = hypothesis.init_state
    length = random.randint(1, state_num * 2)
    for i in range(length):
        action = hypothesis.actions[random.randint(0, len(hypothesis.actions) - 1)]
        time = get_random_delay(upper_guard)
        temp = TimedWord(action, time)
        test.time_words.append(temp)
        test.time_weight += time
        for t in hypothesis.trans:
            if t.source == state and t.is_passing_tran(temp):
                state = t.target
                if state not in state_coverage:
                    state_coverage.append(state)
                if t not in tran_coverage:
                    tran_coverage.append(t)
                break
    test.length = len(test.time_words)
    test.tran_weight = len(tran_coverage)
    test.state_weight = len(state_coverage)
    return test


# random testing method2 - From: Efficient Active Automata Learning via Mutation Testing
def random_testing_2(hypothesis, upper_guard, state_num, system):
    test_num = int(len(hypothesis.states) * len(hypothesis.actions) * upper_guard * 30)
    pretry = 0.9
    pstop = 0.05
    linfix = math.ceil(state_num / 2)
    max_steps = int(2.0 * state_num)

    ctx = None
    for i in range(test_num):
        test = test_generation_2(hypothesis, pretry, pstop, max_steps, linfix, upper_guard)
        flag = test_execution(hypothesis, system, test)
        if flag:
            ctx = test
            return False, ctx
    return True, ctx


# test-case generation（random testing method2）
def test_generation_2(hypothesis, pretry, pstop, max_steps, linfix, upper_guard):
    test = TestInfo([])
    tran_coverage = []
    state_coverage = []
    hypothesis = copy.deepcopy(hypothesis)
    li = random.randint(1, linfix)
    now_time = 0
    state = hypothesis.init_state
    if coin_flip(0.5):
        actions = []
        for i in range(li):
            actions.append(random.choice(hypothesis.actions))
        for action in actions:
            time = get_random_delay(upper_guard)
            temp_DTW = TimedWord(action, time)
            temp_LTW = TimedWord(action, now_time + time)
            test.time_words.append(temp_DTW)
            test.time_weight += time
            for t in hypothesis.trans:
                if t.source == state and t.is_passing_tran(temp_LTW):
                    state = t.target
                    if t.reset:
                        now_time = 0
                    else:
                        now_time = temp_LTW.time
                    if state not in state_coverage:
                        state_coverage.append(state)
                    if t not in tran_coverage:
                        tran_coverage.append(t)
                    break
    while True:
        rS = random.choice(hypothesis.states)
        p0, now_time = find_path_old(hypothesis, upper_guard, now_time, state, rS)
        if p0:
            for p in p0:
                temp_LTW = TimedWord(p.action, now_time + p.time)
                test.time_weight += p.time
                for tran in hypothesis.trans:
                    if tran.is_passing_tran(temp_LTW):
                        state = tran.target
                        if state not in state_coverage:
                            state_coverage.append(state)
                        if tran not in tran_coverage:
                            tran_coverage.append(tran)
                        if tran.reset:
                            now_time = 0
                        else:
                            now_time = temp_LTW.time
                        break
            li = random.randint(1, linfix)
            rSteps_i = []
            for i in range(li):
                rSteps_i.append(random.choice(hypothesis.actions))
            rSteps = []
            for rsi in rSteps_i:
                time = get_random_delay(upper_guard)
                rsi_temp_DTW = TimedWord(rsi, time)
                rsi_temp_LTW = TimedWord(rsi, now_time + time)
                test.time_weight += time
                rSteps.append(rsi_temp_DTW)
                for t in hypothesis.trans:
                    if t.source == state and t.is_passing_tran(rsi_temp_LTW):
                        state = t.target
                        if t.reset:
                            now_time = 0
                        else:
                            now_time = rsi_temp_LTW.time
                        if state not in state_coverage:
                            state_coverage.append(state)
                        if t not in tran_coverage:
                            tran_coverage.append(t)
                        break
            #test = test + p0 + rSteps
            test.time_words.extend(p0 + rSteps)
            if len(test.time_words) > max_steps:
                break
            elif coin_flip(pstop):
                break
        elif coin_flip(1 - pretry):
            break
    test.length = len(test.time_words)
    test.tran_weight = len(tran_coverage)
    test.state_weight = len(state_coverage)
    return test


# random testing method3 - From:Active Model Learning of Timed Automata via Genetic Programming
def random_testing_3(hypothesis, upper_guard, state_num, system):
    test_num = int(len(hypothesis.states) * len(hypothesis.actions) * upper_guard * 10)
    n_len = int(state_num * 2)
    p_valid = 0.9
    p_delay = 0.6

    ctx = None
    for i in range(test_num):
        test = test_generation_3(hypothesis, n_len, p_valid, p_delay, upper_guard)
        flag = test_execution(hypothesis, system, test)
        if flag:
            ctx = test
            return False, ctx
    return True, ctx


# test-case generation（random testing method3）
def test_generation_3(hypothesis, n_len, p_valid, p_delay, upper_guard):
    test = []
    state_now = hypothesis.init_state
    time_now = 0
    while len(test) < n_len:
        transition = None
        delay = get_random_delay(upper_guard)
        transition_list = get_transition_list(hypothesis, state_now)
        if random.random() <= p_valid:
            if random.random() <= p_delay:
                delay_list = get_delay_list(transition_list)
                if len(delay_list) > 0:
                    delay = random.choice(delay_list)
            cur_time = time_now + delay
            transition_valid_list = []
            for tran in transition_list:
                for guard in tran.guards:
                    if guard.is_in_interval(cur_time):
                        if tran.target != tran.source or tran.reset:
                            transition_valid_list.append(tran)
                            break
            if len(transition_valid_list) > 0:
                transition = random.choice(transition_valid_list)

        if transition is None:
            cur_time = time_now + delay
            transition_invalid_list = []
            for tran in transition_list:
                if tran.target == tran.source and not tran.reset:
                    for guard in tran.guards:
                        if guard.is_in_interval(cur_time):
                            transition_invalid_list.append(tran)
                            break
            if len(transition_invalid_list) > 0:
                transition = random.choice(transition_invalid_list)

        if transition is not None:
            test.append(TimedWord(transition.action, delay))
            if transition.reset:
                time_now = 0
            else:
                time_now = time_now + delay
            state_now = transition.target
    return test


# random testing method4 - adapt from random testing method2
def random_testing_4(hypothesis, upper_guard, state_num, pre_ctx, system):
    test_num = int(len(hypothesis.states) * len(hypothesis.actions) * upper_guard * 30)
    pstart = 0.4
    pstop = 0.05
    pvalid = 0.8
    max_steps = min(int(2 * state_num), int(2 * len(hypothesis.states)))

    ctx = None

    tests = []
    tests_random = []
    for i in range(test_num):
        tests.append(test_generation_4(hypothesis, pstart, pstop, pvalid, max_steps, upper_guard, pre_ctx))
        tests_random.append(tests[i].time_words)
    equivalent, ctx = test_execution_list(hypothesis, system, tests_random)

    return equivalent, ctx


# test-case generation 4
def test_generation_4(hypothesis, p_start, pstop, pvalid, max_steps, upper_guard, pre_ctx):
    test = TestInfo([])
    hypothesis = copy.deepcopy(hypothesis)
    # Group migrations by location / validity
    invalid_tran_dict = {}
    valid_tran_dict = {}
    tran_dict = {}
    for state in hypothesis.states:
        invalid_tran_dict[state] = []
        valid_tran_dict[state] = []
        tran_dict[state] = []
    for tran in hypothesis.trans:
        if tran.source == hypothesis.sink_state or tran.target == hypothesis.sink_state:
            invalid_tran_dict[tran.source].append(tran)
        else:
            valid_tran_dict[tran.source].append(tran)
        tran_dict[tran.source].append(tran)

    # begin
    tran_coverage = []
    state_coverage = []
    now_time = 0
    state = hypothesis.init_state
    state_coverage.append(state)
    non_passed_state = copy.deepcopy(hypothesis.states)
    non_passed_state.remove(state)
    # Whether to start from the previous ctx
    if coin_flip(p_start) and len(pre_ctx) < max_steps:
        for t in pre_ctx:
            test.time_weight += t.time
            temp_LTW = TimedWord(t.action, now_time + t.time)
            for tran in tran_dict[state]:
                if tran.is_passing_tran(temp_LTW):
                    state = tran.target
                    if tran.reset:
                        now_time = 0
                    else:
                        now_time = temp_LTW.time
                    if state not in state_coverage:
                        state_coverage.append(state)
                    if tran not in tran_coverage:
                        tran_coverage.append(tran)
                    break
            if state in non_passed_state:
                non_passed_state.remove(state)
        test.time_words.extend(pre_ctx)
    # random walking
    while len(test.time_words) < max_steps:
        if coin_flip(pvalid):
            if valid_tran_dict[state]:
                next_tran = random.choice(valid_tran_dict[state])
                delay_time = get_time_from_tran(next_tran, now_time, upper_guard)
                if delay_time is None:
                    continue
                test.time_weight += delay_time
                test.time_words.append(TimedWord(next_tran.action, delay_time))
                state = next_tran.target
                if next_tran.reset:
                    now_time = 0
                else:
                    now_time += delay_time
                if state not in state_coverage:
                    state_coverage.append(state)
                if next_tran not in tran_coverage:
                    tran_coverage.append(next_tran)
            else:
                continue
        else:
            if invalid_tran_dict[state]:
                next_tran = random.choice(invalid_tran_dict[state])
                delay_time = get_time_from_tran(next_tran, now_time, upper_guard)
                if delay_time is None:
                    continue
                test.time_weight += delay_time
                test.time_words.append(TimedWord(next_tran.action, delay_time))
                state = next_tran.target
                if next_tran.reset:
                    now_time = 0
                else:
                    now_time += delay_time
                if state not in state_coverage:
                    state_coverage.append(state)
                if next_tran not in tran_coverage:
                    tran_coverage.append(next_tran)
            else:
                continue
        if state in non_passed_state:
            non_passed_state.remove(state)
        if coin_flip(pstop):
            break
    # Choose a new location and find the path
    if non_passed_state:
        target_state = random.choice(non_passed_state)
        path_dtw = find_path(hypothesis, upper_guard, now_time, state, target_state, tran_dict)
        if path_dtw:
            test.time_words.extend(path_dtw)
            for p in path_dtw:
                temp_LTW = TimedWord(p.action, now_time + p.time)
                test.time_weight += p.time
                for tran in tran_dict[state]:
                    if tran.is_passing_tran(temp_LTW):
                        state = tran.target
                        if state not in state_coverage:
                            state_coverage.append(state)
                        if tran not in tran_coverage:
                            tran_coverage.append(tran)
                        if tran.reset:
                            now_time = 0
                        else:
                            now_time = temp_LTW.time
                        break
    test.length = len(test.time_words)
    test.tran_weight = len(tran_coverage)
    test.state_weight = len(state_coverage)
    return test


def test_generation_4_old(hypothesis, p_start, pstop, pvalid, max_steps, upper_guard, pre_ctx):
    test = []
    hypothesis = copy.deepcopy(hypothesis)
    invalid_tran_dict = {}
    valid_tran_dict = {}
    tran_dict = {}
    for state in hypothesis.states:
        invalid_tran_dict[state] = []
        valid_tran_dict[state] = []
        tran_dict[state] = []
    for tran in hypothesis.trans:
        if tran.source == hypothesis.sink_state or tran.target == hypothesis.sink_state:
            invalid_tran_dict[tran.source].append(tran)
        else:
            valid_tran_dict[tran.source].append(tran)
        tran_dict[tran.source].append(tran)

    now_time = 0
    state = hypothesis.init_state
    non_passed_state = copy.deepcopy(hypothesis.states)
    non_passed_state.remove(state)

    if coin_flip(p_start) and len(pre_ctx) < max_steps:
        for t in pre_ctx:
            temp_LTW = TimedWord(t.action, now_time + t.time)
            for tran in tran_dict[state]:
                if tran.is_passing_tran(temp_LTW):
                    state = tran.target
                    if tran.reset:
                        now_time = temp_LTW.time
                    else:
                        now_time = 0
                    break
            if state in non_passed_state:
                non_passed_state.remove(state)
        test = test + pre_ctx

    while len(test) < max_steps:
        if coin_flip(pvalid):
            if valid_tran_dict[state]:
                next_tran = random.choice(valid_tran_dict[state])
                delay_time = get_time_from_tran(next_tran, now_time, upper_guard)
                if delay_time is None:
                    continue
                test.append(TimedWord(next_tran.action, delay_time))
                state = next_tran.target
                if next_tran.reset:
                    now_time = 0
                else:
                    now_time += delay_time
            else:
                continue
        else:
            if invalid_tran_dict[state]:
                next_tran = random.choice(invalid_tran_dict[state])
                delay_time = get_time_from_tran(next_tran, now_time, upper_guard)
                if delay_time is None:
                    continue
                test.append(TimedWord(next_tran.action, delay_time))
                state = next_tran.target
                if next_tran.reset:
                    now_time = 0
                else:
                    now_time += delay_time
            else:
                continue
        if state in non_passed_state:
            non_passed_state.remove(state)
        if coin_flip(pstop):
            break

    if non_passed_state:
        target_state = random.choice(non_passed_state)
        path_dtw = find_path(hypothesis, upper_guard, now_time, state, target_state, tran_dict)
        if path_dtw:
            test.extend(path_dtw)
    return test


# test_execution
def test_execution(hypothesis, system, sample):
    system_res, real_value = system.test_DTWs(sample)
    hypothesis_res, value = hypothesis.test_DTWs(sample)
    return real_value != value

def test_execution_list(hypothesis, system, tests):
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


# --------------------------------- auxiliary function ---------------------------------

def coin_flip(p):
    return random.random() <= p


def get_random_delay(upper_guard):
    time = random.randint(0, upper_guard * 3 + 1)
    if time % 2 == 0:
        time = time // 2
    else:
        time = time // 2 + 0.5
    return time


# prefix set of tws
def prefixes(tws):
    new_prefixes = []
    for i in range(1, len(tws) + 1):
        temp_tws = tws[:i]
        new_prefixes.append(temp_tws)
    return new_prefixes


# find a path from s1 to s2
def find_path(hypothesis, upper_guard, now_time, s1, s2, tran_dict):
    if s1 == hypothesis.sink_state and s2 != hypothesis.sink_state:
        return []

    init_now_time = now_time
    visited = []
    next_to_explore = queue.Queue()
    next_to_explore.put([s1, init_now_time, []])
    for state in hypothesis.states:
        random.shuffle(tran_dict[state])
    while not next_to_explore.empty():
        [sc, n_time, paths] = next_to_explore.get()
        if paths is None:
            paths = []
        if sc not in visited:
            visited.append(sc)
            for ts in tran_dict[sc]:
                sn = ts.target
                delay_time = get_time_from_tran(ts, n_time, upper_guard)
                if delay_time is None:
                    continue
                temp_DTW = TimedWord(ts.action, delay_time)
                if ts.reset:
                    n_time = 0
                else:
                    n_time += delay_time
                if sn == s2:
                    paths.append(temp_DTW)
                    return paths
                next_to_explore.put([sn, n_time, copy.deepcopy(paths).append(temp_DTW)])
    return []


# find a path from s1 to s2
def find_path_old(hypothesis, upper_guard, now_time, s1, s2):
    init_now_time = now_time
    visited = []
    next_to_explore = queue.Queue()
    next_to_explore.put([s1, []])

    while not next_to_explore.empty():
        [sc, path] = next_to_explore.get()
        if path is None:
            path = []
        if sc not in visited:
            visited.append(sc)
            for i in hypothesis.actions:
                time = get_random_delay(upper_guard)
                temp_DTW = TimedWord(i, time)
                temp_LTW = TimedWord(i, time + now_time)
                sn = None
                for ts in hypothesis.trans:
                    if ts.source == sc and ts.is_passing_tran(temp_LTW):
                        sn = ts.target
                        if ts.reset:
                            now_time = 0
                        else:
                            now_time = temp_LTW.time
                        break
                if sn == s2:
                    path.append(temp_DTW)
                    return path, now_time
                next_to_explore.put([sn, copy.deepcopy(path).append(temp_DTW)])
    return None, init_now_time


def get_transition_list(hypothesis, state_now):
    transition_list = []
    for tran in hypothesis.trans:
        if tran.source == state_now:
            transition_list.append(tran)
    return transition_list


def get_delay_list(transition_list):
    delay_list = []
    for transition in transition_list:
        for guard in transition.guards:
            left = guard.guard.split(',')[0]
            right = guard.guard.split(',')[1]
            if left[0] == '(':
                delay_list.append(guard.get_min() + 0.5)
            else:
                delay_list.append(guard.get_min())
            if right[-1] == ']':
                delay_list.append(guard.get_max())
            else:
                if right[0] != '+':
                    delay_list.append(guard.get_max() - 0.5)
    return delay_list


def get_time_from_tran(tran, now_time, upper_guard):
    valid_guards = []
    for guard in tran.guards:
        if guard.get_max() < now_time:
            continue
        elif guard.get_max() == now_time and not guard.get_closed_max():
            continue
        valid_guards.append(guard)
    if not valid_guards:
        return None
    guard = random.choice(valid_guards)

    cur_min = guard.get_min() if guard.closed_min else guard.get_min() + 0.5
    if cur_min < now_time:
        cur_min = now_time
    if guard.get_max() == float("inf"):
        return random.randint(0, upper_guard * 3 + 1) / 2
    else:
        cur_max = guard.get_max() if guard.get_closed_max() else guard.get_max() - 0.5
        time = random.randint(cur_min * 2, cur_max * 2)
        return time / 2 - now_time
