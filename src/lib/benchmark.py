import jaxopt
import jax
import jax.numpy as jnp

import time

from problem import Problem
import methods as _methods

# from benchmark_target import BenchmarkTarget
import metrics as _metrics
from benchmark_result import BenchmarkResult
import custom_optimizer


class Benchmark:
    """
    A class that provides the benchmarking of different optimization
    methods on a given problem (like Problem object).
    """

    problem: Problem = None  # Problem to solve
    methods: list[dict[str : dict[str:any]]] = None  # Methods for benchmarking
    available_built_in_methods: list[str] = None # method's keywords. 
    # If you want to call a method from the jaxopt, 
    # the name of the method must begin with one of these keywords.
    metrics: list[str] = None  # List of fields to include in BenchamrkResult

    def __init__(
        self,
        problem: Problem,
        methods: list[dict[str : dict[str:any]]],
        metrics: list[str],
    ) -> None:
        self.problem = problem
        methods_names = list()
        for item in methods:
            for name, params in item.items():
                methods_names.append(name)
        if not _methods.check_method(methods_names):
            exit(1)
        self.methods = methods
        self.available_built_in_methods = _methods.available_built_in_methods
        if not _metrics.check_metric(metrics):
            exit(1)
        self.metrics = metrics

    def __run_solver(
        self, solver, x_init, metrics: list[str], *args, **kwargs
    ) -> dict[str, list[any]]:
        """
        A layer for pulling the necessary information according to metrics
        as the "method" solver works (solver like jaxopt.GradientDescent obj
        or or an heir to the CustomOptimizer class)
        """
        custom_method = issubclass(type(solver), custom_optimizer.CustomOptimizer)
        result = dict()
        start_time = time.time()
        state = solver.init_state(x_init, *args, **kwargs)
        sol = x_init
        if custom_method and sol is None:
            sol = solver.x_init
        
        x_prev = sol

        @jax.jit
        def jitted_update(sol, state):
            return solver.update(sol, state, *args, **kwargs)
        
        def update(sol, state):
            return solver.update(sol, state, *args, **kwargs)


        def stop_criterion(err, tol):
            return err < tol

        tol = 1e-3
        
        if not custom_optimizer and 'tol' in kwargs:
            tol = kwargs['tol']
        
        print(tol)
        for i in range(solver.maxiter):
            if i > 0:
                if not custom_method and stop_criterion(state.error, tol):
                    break
                if custom_method and solver.stop_criterion(sol, state):
                    break
            x_prev = sol
            if custom_method:
                sol, state = update(sol, state)
            else:
                sol, state = jitted_update(sol, state)

            if "history_x" in metrics:
                if not "history_x" in result:
                    result["history_x"] = [sol]
                else:
                    result["history_x"].append(sol)
            if "history_f" in metrics:
                if not "history_f" in result:
                    result["history_f"] = [self.problem.f(sol)]
                else:
                    result["history_f"].append(self.problem.f(sol))
            if "nit" in metrics:
                if not "nit" in result:
                    result["nit"] = [1]
                else:
                    result["nit"][0] += 1
            if "nfev" in metrics:
                # IDK
                pass
            if "njev" in metrics:
                # IDK
                pass
            if "nhev" in metrics:
                # IDK
                pass
            if "errors" in metrics:
                if not "errors" in result:
                    result["errors"] = [state.error]
                else:
                    result["errors"].append(state.error)
        duration = time.time() - start_time
        if "time" in metrics:
            result["time"] = [duration]

        return result

    def run(self, user_method = None) -> BenchmarkResult:
        res = BenchmarkResult(problem=self.problem, methods=list(), metrics=self.metrics)
        data = dict()
        data[self.problem] = dict()
        # methods: list[dict[method(str) : dict[str:any]]]
        for item in self.methods:
            for method, params in item.items():
                # data: dict[Problem, dict[method(str), dict[str, list[any]]]]
                if method.startswith('GRADIENT_DESCENT'):
                    res.methods.append(method)
                    x_init = None
                    if 'x_init' in params:
                        x_init = params['x_init']
                        params.pop('x_init')
                    solver = jaxopt.GradientDescent(fun=self.problem.f, **params)
                    sub = self.__run_solver(solver=solver, x_init=x_init, metrics=self.metrics, **params)    
                    data[self.problem][method] = sub
                elif user_method is not None:
                    res.methods.append(method)
                    x_init = None
                    if 'x_init' in params:
                        x_init = jnp.array(params['x_init'])
                        params.pop('x_init')
                    sub = self.__run_solver(solver=user_method, metrics=self.metrics, x_init=x_init, **params)
                    data[self.problem][method] = sub
        res.data = data
        return res


def test_local():
    from problems.quadratic_problem import QuadraticProblem

    n = 2
    x_init = jnp.array([1.0, 1.0])
    problem = QuadraticProblem(n=n)
    benchamrk = Benchmark(
        problem=problem,
        methods=[
            {
                'GRADIENT_DESCENT_const_step': {
                    'x_init' : x_init,
                    'tol': 1e-2,
                    'maxiter': 11,
                    'stepsize' : 1e-2
                }
            },
            {
                'GRADIENT_DESCENT_adaptive_step': {
                    'x_init' : x_init,
                    'tol': 1e-2,
                    'maxiter': 11,
                    'stepsize' : lambda iter_num: 1 / (iter_num + 20)
                }
            }
        ],
        metrics=[
            "nit",
            "history_x",
            "history_f",
        ],
    )
    result = benchamrk.run()
    result.save("GD_quadratic.json")


if __name__ == "__main__":
    test_local()
