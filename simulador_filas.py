import heapq
from collections import defaultdict
import random

def run_simulation(seed=None):
    """
    Simulador de Rede de Filas - G/G/c/K

    Topologia:
      Chegadas externas (U[2,4]min) --> Fila 1 (G/G/1, serv U[1,2]min)
      Fila 1 --> 0.8 --> Fila 2 (G/G/2/5, serv U[4,6]min)
      Fila 1 --> 0.2 --> Fila 3 (G/G/2/10, serv U[5,15]min)
      Fila 2 --> 0.3 --> Fila 1 (realimentacao)
      Fila 2 --> 0.2 --> Saida
      Fila 2 --> 0.5 --> Fila 3
      Fila 3 --> 0.7 --> Fila 2
      Fila 3 --> 0.3 --> Saida

    Primeiro cliente: t=2.0
    Criterio de parada: 100.000 numeros aleatorios usados
    """
    rng = random.Random(seed)

    MAX_RANDOMS = 100_000
    rand_count = [0]
    stop_flag = [False]

    def get_rand():
        if stop_flag[0]:
            return None
        rand_count[0] += 1
        if rand_count[0] >= MAX_RANDOMS:
            stop_flag[0] = True
        return rng.random()

    def uniform(a, b):
        r = get_rand()
        if r is None:
            return None
        return a + (b - a) * r

    # Configuracoes das filas
    configs = {
        1: {'servers': 1, 'capacity': float('inf'), 'svc_min': 1, 'svc_max': 2},
        2: {'servers': 2, 'capacity': 5,            'svc_min': 4, 'svc_max': 6},
        3: {'servers': 2, 'capacity': 10,           'svc_min': 5, 'svc_max': 15},
    }

    # Estado das filas
    n_sys    = {1: 0, 2: 0, 3: 0}
    n_svc    = {1: 0, 2: 0, 3: 0}
    n_wait   = {1: [], 2: [], 3: []}
    n_lost   = {1: 0, 2: 0, 3: 0}
    n_served = {1: 0, 2: 0, 3: 0}
    n_arrived= {1: 0, 2: 0, 3: 0}

    state_time = {i: defaultdict(float) for i in [1,2,3]}
    last_t     = {1: 0.0, 2: 0.0, 3: 0.0}

    events = []
    ev_seq = [0]
    current_time = [2.0]

    def schedule(t, etype, qid):
        ev_seq[0] += 1
        heapq.heappush(events, (t, ev_seq[0], etype, qid))

    def record(qid, t):
        state_time[qid][n_sys[qid]] += t - last_t[qid]
        last_t[qid] = t

    def arrive_at(qid, t):
        if stop_flag[0]:
            return
        current_time[0] = max(current_time[0], t)
        record(qid, t)
        cfg = configs[qid]
        n_arrived[qid] += 1
        if n_sys[qid] < cfg['capacity']:
            n_sys[qid] += 1
            if n_svc[qid] < cfg['servers']:
                n_svc[qid] += 1
                svc = uniform(cfg['svc_min'], cfg['svc_max'])
                if svc is not None:
                    schedule(t + svc, 'DEP', qid)
                else:
                    n_svc[qid] -= 1
                    n_sys[qid] -= 1
            else:
                n_wait[qid].append(t)
        else:
            n_lost[qid] += 1

    def depart_from(qid, t):
        if stop_flag[0]:
            return
        current_time[0] = max(current_time[0], t)
        record(qid, t)
        n_sys[qid] -= 1
        n_svc[qid] -= 1
        n_served[qid] += 1

        # Rotear cliente
        r = get_rand()
        if r is not None:
            if qid == 1:
                next_q = 2 if r < 0.8 else 3
                arrive_at(next_q, t)
            elif qid == 2:
                if r < 0.3:
                    arrive_at(1, t)
                elif r < 0.5:
                    pass  # saida (prob 0.2)
                else:
                    arrive_at(3, t)  # prob 0.5
            elif qid == 3:
                if r < 0.7:
                    arrive_at(2, t)
                # else saida (prob 0.3)

        # Atender proximo da fila
        if n_wait[qid] and not stop_flag[0]:
            n_wait[qid].pop(0)
            n_svc[qid] += 1
            cfg = configs[qid]
            svc = uniform(cfg['svc_min'], cfg['svc_max'])
            if svc is not None:
                schedule(t + svc, 'DEP', qid)
            else:
                n_svc[qid] -= 1

    # Primeiro cliente chega em t=2.0
    arrive_at(1, 2.0)

    # Proxima chegada externa
    ia = uniform(2, 4)
    if ia is not None:
        schedule(2.0 + ia, 'EXT', 1)

    # Loop principal
    while events and not stop_flag[0]:
        t, _, etype, qid = heapq.heappop(events)
        if etype == 'EXT':
            arrive_at(qid, t)
            if not stop_flag[0]:
                ia = uniform(2, 4)
                if ia is not None:
                    schedule(t + ia, 'EXT', 1)
        elif etype == 'DEP':
            depart_from(qid, t)

    # Registrar estado final
    for i in [1,2,3]:
        record(i, current_time[0])

    return {
        'time':       current_time[0],
        'rand_used':  rand_count[0],
        'state_time': {i: dict(state_time[i]) for i in [1,2,3]},
        'lost':       dict(n_lost),
        'served':     dict(n_served),
        'arrived':    dict(n_arrived),
        'remaining':  {i: n_sys[i] for i in [1,2,3]},
    }


def format_results(res):
    sim_time = res['time']
    print("=" * 65)
    print("  RESULTADO DA SIMULACAO - REDE DE FILAS")
    print("=" * 65)
    print(f"\n  Tempo global de simulacao : {sim_time:.4f} min")
    print(f"  Numeros aleatorios usados : {res['rand_used']}")

    names = {
        1: "Fila 1  G/G/1    (chegadas U[2,4], serv U[1,2])",
        2: "Fila 2  G/G/2/5  (serv U[4,6])",
        3: "Fila 3  G/G/2/10 (serv U[5,15])",
    }

    for qid in [1, 2, 3]:
        print(f"\n{'─'*65}")
        print(f"  {names[qid]}")
        print(f"{'─'*65}")
        print(f"  Clientes chegados  : {res['arrived'][qid]}")
        print(f"  Clientes atendidos : {res['served'][qid]}")
        print(f"  Clientes perdidos  : {res['lost'][qid]}")
        print(f"  No sistema ao fim  : {res['remaining'][qid]}")

        st = res['state_time'][qid]
        total = sum(st.values())
        if total > 0:
            print(f"\n  Distribuicao de probabilidades dos estados:")
            print(f"  {'Estado(n)':>10}  {'Tempo acumulado(min)':>22}  {'Probabilidade':>14}")
            print(f"  {'-'*10}  {'-'*22}  {'-'*14}")
            for k in sorted(st.keys()):
                prob = st[k] / total
                print(f"  {k:>10}  {st[k]:>22.4f}  {prob:>14.6f}")
            print(f"  {'TOTAL':>10}  {total:>22.4f}  {'1.000000':>14}")

    print(f"\n{'='*65}\n")


if __name__ == "__main__":
    print("Executando simulacao com 100.000 numeros aleatorios...\n")
    resultado = run_simulation(seed=42)
    format_results(resultado)
