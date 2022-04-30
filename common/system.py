from common.TimedWord import TimedWord, ResetTimedWord
from common.TimeInterval import Guard, complement_intervals
from common.hypothesis import OTA, OTATran


class System(object):
    def __init__(self, actions, states, trans, init_state, accept_states):
        self.actions = actions
        self.states = states
        self.trans = trans
        self.init_state = init_state
        self.accept_states = accept_states

        self.mq_num = 0
        self.eq_num = 0
        self.test_num = 0
        self.test_num_cache = 0
        self.action_num = 0
        self.cache = {}
        self.total_time = 0

    # Perform tests(DTWs) on the system, return value and DRTWs(full)
    def test_DTWs(self, DTWs):
        self.test_num += 1
        tuple_DTWs = tuple(DTWs)
        if tuple_DTWs in self.cache:
            return self.cache[tuple_DTWs][0], self.cache[tuple_DTWs][1]
        self.test_num_cache += 1

        DRTWs = []
        value = []
        now_time = 0
        cur_state = self.init_state
        for dtw in DTWs:
            self.action_num += 1
            self.total_time += dtw.time
            time = dtw.time + now_time
            new_LTW = TimedWord(dtw.action, time)
            flag = False
            for tran in self.trans:
                if tran.source == cur_state and tran.is_passing_tran(new_LTW):
                    flag = True
                    cur_state = tran.target
                    if tran.reset:
                        now_time = 0
                        reset = True
                    else:
                        now_time = time
                        reset = False
                    DRTWs.append(ResetTimedWord(dtw.action, dtw.time, reset))

                    break
            if not flag:
                DRTWs.append(ResetTimedWord(dtw.action, dtw.time, True))
                value.append(-1)
                break
            else:
                if cur_state in self.accept_states:
                    value.append(1)
                else:
                    value.append(0)
        # 补全
        len_diff = len(DTWs) - len(DRTWs)
        if len_diff != 0:
            temp = DTWs[len(DRTWs):]
            for i in temp:
                value.append(-1)
                DRTWs.append(ResetTimedWord(i.action, i.time, True))
        self.cache[tuple_DTWs] = [DRTWs, value]
        return DRTWs, value

    # Perform tests(LTWs) on the system(smart teacher), return value and LRTWs
    def test_LTWs(self, LTWs):
        self.mq_num += 1
        if not LTWs:
            if self.init_state in self.accept_states:
                value = 1
            else:
                value = 0
            return [], value
        LRTWs = []
        value = None
        now_time = 0
        cur_state = self.init_state
        for ltw in LTWs:
            if ltw.time < now_time:
                value = -1
                LRTWs.append(ResetTimedWord(ltw.action, ltw.time, True))
                break
            else:
                DTW = TimedWord(ltw.action, ltw.time - now_time)
                cur_state, value, reset = self.test_DTW(DTW, now_time, cur_state)
                if reset:
                    LRTWs.append(ResetTimedWord(ltw.action, ltw.time, True))
                    now_time = 0
                else:
                    LRTWs.append(ResetTimedWord(ltw.action, ltw.time, False))
                    now_time = ltw.time
                if value == -1:
                    break
        # 补全
        len_diff = len(LTWs) - len(LRTWs)
        if len_diff != 0:
            temp = LTWs[len(LRTWs):]
            for i in temp:
                LRTWs.append(ResetTimedWord(i.action, i.time, True))
        return LRTWs, value

    # input -> DTW(single)，output -> curState and value - for logical-timed test
    def test_DTW(self, DTW, now_time, cur_state):
        value = None
        reset = False
        tran_flag = False  # tranFlag为true表示有这样的迁移
        LTW = TimedWord(DTW.action, DTW.time + now_time)
        for tran in self.trans:
            if tran.source == cur_state and tran.is_passing_tran(LTW):
                tran_flag = True
                cur_state = tran.target
                reset = True if tran.reset else False
                break
        if not tran_flag:
            value = -1
            cur_state = 'sink'
            reset = True
        if cur_state in self.accept_states:
            value = 1
        elif cur_state != 'sink':
            value = 0
        return cur_state, value, reset

    # Get the max time value constant appearing in OTA.
    def max_time_value(self):
        max_time_value = 0
        for tran in self.trans:
            for c in tran.guards:
                if c.max_value == '+':
                    temp_max_value = float(c.min_value)
                else:
                    temp_max_value = float(c.max_value)
                if max_time_value < temp_max_value:
                    max_time_value = temp_max_value
        return max_time_value + 1

    # Get the minimal region num of a (finite) time guard
    def get_minimal_region_num(self):
        res = float('inf')
        for tran in self.trans:
            for guard in tran.guards:
                if guard.get_region_num() < res:
                    res = guard.get_region_num()
        if res == float('inf'):
            res = 1
        return res

    # Get the minimal region num of a (finite) time guard
    def get_minimal_duration(self, upper_guard):
        res = float('inf')
        for tran in self.trans:
            for guard in tran.guards:
                if guard.get_min() != 0 and guard.get_min() < res:
                    res = guard.get_min()
                if guard.get_max() - guard.get_min() < res:
                    res = guard.get_max() - guard.get_min()
                if 0 <= upper_guard - guard.get_max() < res:
                    res = upper_guard - guard.get_max()
        if res == float('inf') or res == 0:
            res = 1
        return res


class SysTran(object):
    def __init__(self, tran_id, source, action, guards, reset, target):
        self.tran_id = tran_id
        self.source = source
        self.action = action
        self.guards = guards
        self.reset = reset
        self.target = target

    def is_passing_tran(self, tw):
        if tw.action == self.action:
            for guard in self.guards:
                if guard.is_in_interval(tw.time):
                    return True
        return False

    def show_guards(self):
        guard_list = self.guards[0].show()
        for i in range(1, len(self.guards)):
            guard_list = guard_list + 'U' + self.guards[i].show()
        return guard_list


# Build system based on json file
def build_system(model):
    actions = model["inputs"]
    states = model["states"]
    init_state = model["initState"]
    accept_states = model["acceptStates"]
    tran_list = model["trans"]

    trans = []
    for tran in tran_list:
        tran_id = str(tran)
        source = tran_list[tran][0]
        target = tran_list[tran][4]
        action = tran_list[tran][1]
        reset = tran_list[tran][3] == "r"
        # time guard
        intervals = tran_list[tran][2]
        intervals_list = intervals.split('U')
        guards = []
        for guard in intervals_list:
            new_guard = Guard(guard.strip())
            guards.append(new_guard)
        trans.append(SysTran(tran_id, source, action, guards, reset, target))
    return System(actions, states, trans, init_state, accept_states)


# make system complete
def build_canonicalOTA(system):
    actions = system.actions
    states = system.states
    trans = system.trans
    init_state = system.init_state
    accept_states = system.accept_states

    sinkFlag = False
    newTrans = []
    sink_state = 'sink'
    tranNumber = len(system.trans)

    for state in system.states:
        guardDict = {}
        for action in actions:
            guardDict[action] = []
        for tran in trans:
            if tran.source == state:
                for action in actions:
                    if tran.action == action:
                        for guard in tran.guards:
                            guardDict[action].append(guard)
        for key, value in guardDict.items():
            if len(value) > 0:
                addGuards = complement_intervals(value)
            else:
                addGuards = [Guard('[0,+)')]
            if len(addGuards) > 0:
                sink_state = 'sink'
                sinkFlag = True
                for guard in addGuards:
                    tempTran = OTATran(tranNumber, state, key, [guard], True, sink_state)
                    tranNumber = tranNumber + 1
                    newTrans.append(tempTran)
    if sinkFlag:
        states.append(sink_state)
        for tran in newTrans:
            trans.append(tran)
        for action in actions:
            guards = [Guard('[0,+)')]
            tempTran = OTATran(tranNumber, sink_state, action, guards, True, sink_state)
            tranNumber = tranNumber + 1
            trans.append(tempTran)
    newOTA = OTA(actions, states, trans, init_state, accept_states, sink_state)
    return newOTA
