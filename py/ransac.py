# -*- coding: utf-8 -*-
"""
Created on 2018-04-21 21:04:04
@Author: ZHAO Lingfeng
@Version : 0.0.1
"""
import random
from copy import deepcopy

import numpy as np
from scipy import linalg


class Ransac:

    def __init__(self, data1: np.ndarray, data2: np.ndarray, max_iter_times=1000):
        """利用Ransac算法求得变换矩阵

        Args:
            data1 (np.ndarray): n*2形状的点数组
            data2 (np.ndarray): n*2形状的点数组
            max_iter_times (int, optional): Defaults to 1000. 最大迭代次数

        Raises:
            ValueError: 输入数组形状不同
        """
        # print(repr(data1), repr(data2))
        self.data1 = data1
        self.data2 = data2
        if(self.data1.shape != self.data2.shape):
            raise ValueError("Argument shape not equal")

        self.points_length = self.data1.shape[0]
        self.good_points = 0
        self.max_iter_times = max_iter_times

        # 0 for not chosen
        self.mask = np.zeros(self.points_length, dtype=np.bool)

    def random_calculate(self, max_try_times=1000)-> np.ndarray:
        """随机取四个点对，计算其变换矩阵
            max_try_times (int, optional): Defaults to 1000. 选取尝试次数

        Returns:
            np.ndarray: 变换矩阵M
        """

        if self.points_length - np.count_nonzero(self.mask) < 4:
            return False

        rand_point = random.sample(range(self.points_length), 4)
        # try_times = 0
        # while np.any(self.mask[rand_point]):
        #     try_times += 1
        #     rand_point = random.sample(range(self.points_length), 4)
        #     if try_times > max_try_times:
        #         return False
        # self.mask[rand_point] = True
        M = self.get_perspective_transform(self.data1[rand_point], self.data2[rand_point])
        return M

    @staticmethod
    def get_perspective_transform(src: np.ndarray, dst: np.ndarray)-> np.ndarray:
        """获取透视变换矩阵

        Args:
            src (np.ndarray): 2*4形状
            dst (np.ndarray): 2*4形状

        Returns:
            np.ndarray: 变换矩阵M
        """
        X = np.array((8, 1), np.float)
        A = np.zeros((8, 8), np.float)
        B = np.zeros((8), np.float)

        for i in range(4):
            A[i][0] = A[i + 4][3] = src[i][0]
            A[i][1] = A[i + 4][4] = src[i][1]
            A[i][2] = A[i + 4][5] = 1
            A[i][3] = A[i][4] = A[i][5] = A[i + 4][0] = A[i + 4][1] = A[i + 4][2] = 0
            A[i][6] = -src[i][0] * dst[i][0]
            A[i][7] = -src[i][1] * dst[i][0]
            A[i + 4][6] = -src[i][0] * dst[i][1]
            A[i + 4][7] = -src[i][1] * dst[i][1]
            B[i] = dst[i][0]
            B[i + 4] = dst[i][1]
        try:
            X = linalg.solve(A, B).copy()
        except Exception as e:
            print("Error when calcuating M: ", e)
            return False
        else:
            X.resize((3, 3), refcheck=False)
            X[2][2] = 1
        return X

    @staticmethod
    def perspective_transform(points: np.ndarray, M: np.ndarray)->np.ndarray:
        """求得在M变换矩阵情况下points数组里每个点的新变换坐标

        Args:
            points (np.ndarray): n*2形状的数组
            M (np.ndarray): 3*3的透视变换矩阵

        Returns:
            np.ndarray: 变换后的点
        """

        array_i = np.hstack((points, np.ones((points.shape[0], 1), dtype=points.dtype))).T
        x = np.dot(M, array_i)
        result = np.vstack((x[0] / x[2], x[1] / x[2])).T
        return result

    # TODO: get a better threshold or dynamic change it
    @classmethod
    def get_good_points(cls, points1: np.ndarray, points2: np.ndarray, M: np.ndarray, threshold=3)-> int:
        """求得在给定变换矩阵下，计算将points1变换后与points2之间的距离

        Args:
            points1 (np.ndarray): n*2形状数组
            points2 (np.ndarray): n*2形状数组
            M (np.ndarray): 3*3透视变换矩阵
            threshold (int, optional): Defaults to 3. 距离阈值

        Returns:
            int: 优秀点个数
        """

        transformed = cls.perspective_transform(points1, M)
        dis = np.sum((transformed - points2) * (transformed - points2), axis=1)
        good = dis < threshold * threshold
        return np.sum(good)

    @staticmethod
    def get_itereration_time(proportion: float, p=0.995, points=4)->int:
        """更新迭代次数

        Args:
            proportion (float): 优秀点比例
            p (float, optional): Defaults to 0.995. 确信值
            points (int, optional): Defaults to 4. 四个点

        Returns:
            int: 更新后的所需迭代次数
        """

        proportion = max(min(proportion, 1), 0)
        p = max(min(p, 1), 0)
        # print(p,proportion)
        k = np.log(1 - p) / np.log(1 - np.power(proportion, 4))
        return int(k)

    def run(self, distance=3)->np.ndarray:
        """进行计算

        Returns:
            计算的透视变换矩阵
        """

        iter_times = 0
        best_M = None
        # random.seed(1)
        while iter_times < self.max_iter_times:
            M = self.random_calculate()
            if M is False:
                return best_M
            good_nums = self.get_good_points(self.data1, self.data2, M, distance)
            if good_nums > self.good_points:
                self.good_points = good_nums
                best_M = M
                self.max_iter_times = min(self.max_iter_times,
                                          self.get_itereration_time(good_nums / self.points_length))
            iter_times += 1

        return best_M


class GeneticRansac(Ransac):

    class Individual:
        def __init__(self, dna, value=0):
            self.dna = dna
            self.value = value

        def __lt__(self, other: 'Individual'):
            return self.value < other.value

        def __repr__(self):
            return "dna: <{}>, value: {}".format(self.dna, self.value)

        __str__ = __repr__

    SAMPLE = 30
    MUTATION_RATE = 0.1

    def __init__(self, data1: np.ndarray, data2: np.ndarray):
        super().__init__(data1, data2)
        if self.points_length > 7:
            self.population = []
            for i in range(self.SAMPLE):
                indv = self.Individual(np.random.choice(range(self.points_length), 4, replace=0))
                self.population.append(indv)

    def run(self):
        # 总数过小
        if self.points_length < 7:
            return super().run()

        for i in range(40):
            # 计算总距离
            for i in self.population:
                M = self.get_perspective_transform(self.data1[i.dna], self.data2[i.dna])
                # 共线或其他失败情况
                if M is not False:
                    good = self.get_good_points(self.data1, self.data2, M)
                    i.value = good
                else:
                    i.value = 0
            self.population = sorted(self.population, reverse=True)

            # 去除一半
            all_value = sum([x.value for x in self.population])
            prop = [x.value / all_value for x in self.population]
            # TODO: 实现轮盘选择
            # self.population = self.population[:self.SAMPLE // 2]
            self.population = np.random.choice(self.population, size=self.SAMPLE // 2, replace=False, p=prop)

            children = []
            # 交叉
            while len(children) + len(self.population) <= self.SAMPLE:
                mother = random.choice(self.population)
                father = random.choice(self.population)
                corss_index = random.choices(range(4), k=2)
                child = deepcopy(mother)
                child.dna[corss_index] = father.dna[corss_index]
                # 变异
                if random.random() < self.MUTATION_RATE:
                    rand_index = random.choice(range(4))
                    rand_point = random.choice(range(self.points_length))
                    while child.dna[rand_index] == rand_point:
                        rand_point = random.choice(range(self.points_length))
                    child.dna[rand_index] = rand_point

                children.append(child)

            self.population = np.concatenate((self.population, children))

        # 获取最优或次优点
        M = self.get_perspective_transform(self.data1[self.population[0].dna], self.data2[self.population[0].dna])

        i = 1
        while M is False:
            M = self.get_perspective_transform(self.data1[self.population[i].dna], self.data2[self.population[i].dna])
            i += 1
            if i > self.SAMPLE:
                raise Exception("GA error!!")
        self.good_points = self.get_good_points(self.data1, self.data2, M)
        return M


def main():
    pass
    test()


def test():
    data_point1 = np.array([[1, 2], [3, 3], [5, 5], [6, 8]])
    data_point2 = np.array([[4, 2], [5, 3], [12, 5], [64, 8]])
    ransac = Ransac(data_point1, data_point2)
    M = ransac.get_perspective_transform(data_point1, data_point2)
    print(M)
    print("Supposed to be:\n",
          "[[-0.76850095,  1.15180266,  1.77229602]\n",
          "[ 0.20777989, -0.31593928,  2.07779886],\n",
          "[-0.10388994, -0.03462998,  1.        ]]")
    print(ransac.get_good_points(data_point1, data_point1, M))

    test_data = np.random.rand(20, 2) * 30
    dst_data = Ransac.perspective_transform(test_data, M)
    dst_data[0] = [21312, 213123]
    ransac = Ransac(test_data, dst_data)
    result_M = ransac.run()
    print("Result M:")
    print(result_M)
    print("Max itereration times")
    print(ransac.max_iter_times)
    # Test for GA
    data1 = np.array([[520.12805, 243.64803], [4679.038, 627.0568], [508.80002, 277.2], [259.78067, 403.10794], [661.2, 199.20001], [695.13727, 232.90681], [831.51373, 134.78401], [512.395, 243.65637], [329.65274, 756.0514], [502., 292.], [523.2, 244.8], [522.72003, 244.8], [1870.3875, 1967.8467], [5208.884, 904.0897], [
                     661., 199.], [1872.2125, 1967.764], [1003.2909, 240.07318], [316., 736.], [612., 170.40001], [520.4737, 244.68483], [534.98895, 199.06564], [523., 245.], [582., 220.], [5072., 756.], [391.68002, 116.64001], [4572.2886, 1094.861], [1871.217, 1968.2616], [1003.2909, 238.87878]], dtype=np.float32)
    data2 = np.array([[1080.0001, 221.18402], [5297.137, 400.12195], [1069.2001, 253.20001], [845.0337, 394.15], [1218., 168.], [1250.5305, 200.65819], [1374.797, 93.31201], [1074.9546, 222.15727], [910.1282, 730.9691], [1093., 177.], [1082., 221.], [1081.4401, 220.32], [2401.2292, 1874.5347], [
                     708., 389.], [1218., 168.], [2403.7178, 1875.1985], [1540.7682, 186.32545], [901., 711.], [1153., 261.], [1078.2721, 221.87523], [1094.8611, 176.67076], [847., 44.], [1426., 175.], [1244.4, 326.40002], [823., 32.], [5173.633, 906.1633], [2401.2292, 1873.7054], [1540.7682, 185.13106]], dtype=np.float32)
    gr = GeneticRansac(data1, data2)
    print(gr.run())


if __name__ == "__main__":
    main()
