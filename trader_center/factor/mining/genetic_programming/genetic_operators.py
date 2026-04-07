"""
遗传操作

实现交叉、变异和选择等遗传操作。
"""

from typing import List, Tuple, Optional
import numpy as np
import random
import copy

from .expression import FactorExpression, ExpressionNode
from .primitives import PrimitiveSet, PrimitiveType


class GeneticOperators:
    """
    遗传操作集合
    
    提供交叉、变异和选择操作。
    
    Example:
        operators = GeneticOperators(pset)
        offspring = operators.crossover(parent1, parent2)
        mutant = operators.mutate(parent, max_depth=3)
    """
    
    def __init__(
        self,
        pset: PrimitiveSet,
        crossover_prob: float = 0.8,
        mutation_prob: float = 0.2,
        max_depth: int = 10,
    ):
        """
        初始化遗传操作
        
        Args:
            pset: 基元集合
            crossover_prob: 交叉概率
            mutation_prob: 变异概率
            max_depth: 最大深度限制
        """
        self.pset = pset
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.max_depth = max_depth
    
    def crossover(
        self,
        parent1: FactorExpression,
        parent2: FactorExpression,
    ) -> Tuple[FactorExpression, FactorExpression]:
        """
        交叉操作
        
        随机选择两个父代的子树进行交换。
        
        Args:
            parent1: 父代1
            parent2: 父代2
        
        Returns:
            两个子代
        """
        if random.random() > self.crossover_prob:
            return parent1.copy(), parent2.copy()
        
        offspring1 = parent1.copy()
        offspring2 = parent2.copy()
        
        nodes1 = offspring1.get_all_nodes()
        nodes2 = offspring2.get_all_nodes()
        
        if not nodes1 or not nodes2:
            return offspring1, offspring2
        
        node1 = random.choice(nodes1)
        node2 = random.choice(nodes2)
        
        if self._would_exceed_depth(node1, node2) or self._would_exceed_depth(node2, node1):
            return offspring1, offspring2
        
        self._swap_subtrees(node1, node2)
        
        return offspring1, offspring2
    
    def mutate(
        self,
        individual: FactorExpression,
        mutation_type: str = 'subtree',
    ) -> FactorExpression:
        """
        变异操作
        
        Args:
            individual: 个体
            mutation_type: 变异类型
                - 'subtree': 子树变异（用随机生成的子树替换）
                - 'point': 点变异（替换单个节点）
                - 'hoist': 提升变异（用子树替换整棵树）
                - 'shrink': 收缩变异（用终端节点替换子树）
        
        Returns:
            变异后的个体
        """
        if random.random() > self.mutation_prob:
            return individual.copy()
        
        offspring = individual.copy()
        
        if mutation_type == 'subtree':
            return self._mutate_subtree(offspring)
        elif mutation_type == 'point':
            return self._mutate_point(offspring)
        elif mutation_type == 'hoist':
            return self._mutate_hoist(offspring)
        elif mutation_type == 'shrink':
            return self._mutate_shrink(offspring)
        else:
            return self._mutate_subtree(offspring)
    
    def _mutate_subtree(self, individual: FactorExpression) -> FactorExpression:
        """子树变异"""
        nodes = individual.get_all_nodes()
        if not nodes:
            return individual
        
        node = random.choice(nodes)
        
        remaining_depth = self.max_depth - self._get_node_depth(node)
        new_subtree = self._generate_random_subtree(max(1, remaining_depth))
        
        if node.parent is None:
            individual.root = new_subtree
        else:
            parent = node.parent
            if node not in parent.children:
                return individual
            idx = parent.children.index(node)
            parent.children[idx] = new_subtree
            new_subtree.parent = parent
        
        return individual
    
    def _mutate_point(self, individual: FactorExpression) -> FactorExpression:
        """点变异"""
        nodes = individual.get_all_nodes()
        if not nodes:
            return individual
        
        node = random.choice(nodes)
        
        if node.is_terminal:
            new_terminal = self.pset.get_random_terminal()
            node.primitive = new_terminal
        else:
            functions_same_arity = [
                f for f in self.pset.functions.values()
                if f.arity == node.arity
            ]
            if functions_same_arity:
                node.primitive = random.choice(functions_same_arity)
        
        return individual
    
    def _mutate_hoist(self, individual: FactorExpression) -> FactorExpression:
        """提升变异"""
        nodes = individual.get_function_nodes()
        if not nodes:
            return individual
        
        node = random.choice(nodes)
        
        if node.children:
            new_root = random.choice(node.children).copy()
            individual.root = new_root
        
        return individual
    
    def _mutate_shrink(self, individual: FactorExpression) -> FactorExpression:
        """收缩变异"""
        nodes = individual.get_function_nodes()
        if not nodes:
            return individual
        
        node = random.choice(nodes)
        
        if node.children:
            terminal = self.pset.get_random_terminal()
            new_node = ExpressionNode(terminal)
            
            if node.parent is None:
                individual.root = new_node
            else:
                parent = node.parent
                idx = parent.children.index(node)
                parent.children[idx] = new_node
                new_node.parent = parent
        
        return individual
    
    def _generate_random_subtree(self, max_depth: int) -> ExpressionNode:
        """生成随机子树"""
        if max_depth == 0:
            terminal = self.pset.get_random_terminal()
            return ExpressionNode(terminal)
        
        if random.random() < 0.3:
            terminal = self.pset.get_random_terminal()
            return ExpressionNode(terminal)
        
        func = self.pset.get_random_function()
        children = []
        for _ in range(func.arity):
            child = self._generate_random_subtree(max_depth - 1)
            children.append(child)
        
        return ExpressionNode(func, children)
    
    def _swap_subtrees(self, node1: ExpressionNode, node2: ExpressionNode):
        """交换两个子树"""
        parent1 = node1.parent
        parent2 = node2.parent
        
        if parent1 is None and parent2 is None:
            return
        
        if parent1 is None:
            if node2 not in parent2.children:
                return
            idx2 = parent2.children.index(node2)
            parent2.children[idx2] = node1
            node1.parent = parent2
            node2.parent = None
        elif parent2 is None:
            if node1 not in parent1.children:
                return
            idx1 = parent1.children.index(node1)
            parent1.children[idx1] = node2
            node2.parent = parent1
            node1.parent = None
        else:
            if node1 not in parent1.children or node2 not in parent2.children:
                return
            idx1 = parent1.children.index(node1)
            idx2 = parent2.children.index(node2)
            
            parent1.children[idx1] = node2
            parent2.children[idx2] = node1
            
            node1.parent = parent2
            node2.parent = parent1
    
    def _get_node_depth(self, node: ExpressionNode) -> int:
        """获取节点深度"""
        depth = 0
        current = node.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth
    
    def _would_exceed_depth(self, node1: ExpressionNode, node2: ExpressionNode) -> bool:
        """检查交换后是否会超过最大深度"""
        depth1 = self._get_subtree_depth(node1)
        depth2 = self._get_subtree_depth(node2)
        node_depth1 = self._get_node_depth(node1)
        node_depth2 = self._get_node_depth(node2)
        
        return (node_depth1 + depth2 > self.max_depth or 
                node_depth2 + depth1 > self.max_depth)
    
    def _get_subtree_depth(self, node: ExpressionNode) -> int:
        """获取子树深度"""
        if node.is_terminal:
            return 1
        return 1 + max(self._get_subtree_depth(child) for child in node.children)


class Selection:
    """
    选择操作
    
    提供多种选择策略。
    """
    
    @staticmethod
    def tournament_selection(
        population: List[FactorExpression],
        tournament_size: int = 3,
    ) -> FactorExpression:
        """
        锦标赛选择
        
        随机选择tournament_size个个体，返回适应度最高的。
        
        Args:
            population: 种群
            tournament_size: 锦标赛大小
        
        Returns:
            选中的个体
        """
        tournament = random.sample(population, min(tournament_size, len(population)))
        return max(tournament, key=lambda x: x.fitness or -np.inf)
    
    @staticmethod
    def roulette_selection(
        population: List[FactorExpression],
    ) -> FactorExpression:
        """
        轮盘赌选择
        
        按适应度比例选择个体。
        
        Args:
            population: 种群
        
        Returns:
            选中的个体
        """
        fitnesses = [max(0, ind.fitness or 0) for ind in population]
        total_fitness = sum(fitnesses)
        
        if total_fitness == 0:
            return random.choice(population)
        
        probs = [f / total_fitness for f in fitnesses]
        return random.choices(population, weights=probs, k=1)[0]
    
    @staticmethod
    def rank_selection(
        population: List[FactorExpression],
    ) -> FactorExpression:
        """
        排名选择
        
        按排名选择个体，避免适应度差异过大导致早熟。
        
        Args:
            population: 种群
        
        Returns:
            选中的个体
        """
        sorted_pop = sorted(population, key=lambda x: x.fitness or -np.inf, reverse=True)
        ranks = list(range(len(sorted_pop), 0, -1))
        total_rank = sum(ranks)
        probs = [r / total_rank for r in ranks]
        return random.choices(sorted_pop, weights=probs, k=1)[0]
    
    @staticmethod
    def elitism_selection(
        population: List[FactorExpression],
        n_elite: int = 1,
    ) -> List[FactorExpression]:
        """
        精英选择
        
        选择适应度最高的n个个体。
        
        Args:
            population: 种群
            n_elite: 精英数量
        
        Returns:
            精英个体列表
        """
        sorted_pop = sorted(population, key=lambda x: x.fitness or -np.inf, reverse=True)
        return [ind.copy() for ind in sorted_pop[:n_elite]]


def apply_genetic_operations(
    population: List[FactorExpression],
    operators: GeneticOperators,
    selection_method: str = 'tournament',
    tournament_size: int = 3,
) -> List[FactorExpression]:
    """
    应用遗传操作生成新一代
    
    Args:
        population: 当前种群
        operators: 遗传操作器
        selection_method: 选择方法
        tournament_size: 锦标赛大小
    
    Returns:
        新一代种群
    """
    new_population = []
    
    while len(new_population) < len(population):
        if selection_method == 'tournament':
            parent1 = Selection.tournament_selection(population, tournament_size)
            parent2 = Selection.tournament_selection(population, tournament_size)
        elif selection_method == 'roulette':
            parent1 = Selection.roulette_selection(population)
            parent2 = Selection.roulette_selection(population)
        else:
            parent1 = Selection.rank_selection(population)
            parent2 = Selection.rank_selection(population)
        
        offspring1, offspring2 = operators.crossover(parent1, parent2)
        
        offspring1 = operators.mutate(offspring1)
        offspring2 = operators.mutate(offspring2)
        
        new_population.extend([offspring1, offspring2])
    
    return new_population[:len(population)]
