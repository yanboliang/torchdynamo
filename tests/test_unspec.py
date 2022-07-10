#!/usr/bin/env pytest
import random

import numpy as np
import torch

import torchdynamo.testing
from torchdynamo.testing import same


class UnspecTests(torchdynamo.testing.TestCase):
    def test_numpy_correctness(self):
        def fn(x, y, z):
            xy = [x + y, y, False]
            np_x = x.numpy()
            np_y = y.numpy()
            return {
                "x": x,
                "z": z,
                "a": np_y.sum(),
                "b": xy,
                "c": np_y[0][0] / 68,
                "d": np_x.sum(),
            }, x + np_y.sum() + z

        x = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float64)
        y = torch.ones([2, 2], dtype=torch.int64)
        z = np.int64(12)
        res1 = fn(x, y, z)
        cnts = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnts):
            res2 = fn(x, y, z)
        self.assertTrue(same(res1, res2))

    def test_no_recompilations(self):
        # no recompilations if passing on different numpy int values
        def fn(x, y):
            return {"a": x + 1, "b": y / 2}

        x = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float64)
        cnts = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnts):
            for i in range(10):
                fn(x, np.int64(i))
        self.assertEqual(cnts.frame_count, 1)
        self.assertEqual(cnts.op_count, 2)

    def test_builtin_max_min(self):
        # test unspecialized primitive max/min
        def fn(x, y, z):
            return z + 1, max(x, y), min(x - 4, y)

        x = np.int64(12)
        y = 10
        z = torch.tensor([[1.0, 2.0], [3.0, 4.0]], dtype=torch.float64)
        res1 = fn(x, y, z)
        cnts = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnts):
            res2 = fn(x, y, z)
        self.assertTrue(same(res1, res2))

    def test_random_values(self):
        # test random functions
        def fn(x):
            r1 = random.random()
            y = x + random.uniform(10, 20)
            r2 = random.randint(2, 18)
            return y + r1, r2

        x = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        random.seed(1)
        res1 = fn(x)
        cnts = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnts):
            random.seed(1)
            res2 = fn(x)
        self.assertTrue(same(res1, res2))

    def test_builtin_getitem(self):
        # builtin getitem args[0] is python list and args[1] is unspec
        def fn(x, idx):
            return (torch.zeros(idx), x[idx])

        x = list(range(50))
        ref = fn(x, 33)  ## 33 is unspecialized
        cnts = torchdynamo.testing.CompileCounter()
        with torchdynamo.optimize(cnts):
            res = fn(x, 33)
        self.assertTrue(same(ref, res))
