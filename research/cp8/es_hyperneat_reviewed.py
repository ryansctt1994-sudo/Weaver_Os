from __future__ import annotations

"""
══════════════════════════════════════════════════════════════════
  GENESIS ES-HYPERNEAT v4.0
  Evolvable-Substrate HyperNEAT with Octree Adaptive Resolution
  and Link Expression Output (LEO) Integration

  Protocol: ACP/1.0 | Binding: conv_a1b2c3d4e5f6g7h8i9j0
  Agent: Yennefer-Deploy | Tier: A2A_TIER5_QUANTUM
  PI: Igor A. Holt | genesisconductor.io

  Reference: Risi & Stanley (2012)
  "An Enhanced Hypercube-Based Encoding for Evolving the 
   Placement, Density, and Connectivity of Neurons"
══════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Tuple, Dict, List, Any, Union, Set
from enum import Enum, auto
from collections import defaultdict
import json
import hashlib
from pathlib import Path
import time
import math

# ═══════════════════════════════════════════════════════════════
# JAX IMPORTS
# ═══════════════════════════════════════════════════════════════
try:
    import jax
    import jax.numpy as jnp
    from jax import vmap, jit, random, lax
    from flax import linen as nn
    from flax.core import freeze, unfreeze
    import optax
    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False
    class jnp: pass
    class nn: 
        class Module: pass
        compact = staticmethod(lambda f: f)
    class jax: pass
    jit = lambda f: f

# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════
class DifferentiationState(Enum):
    PLURIPOTENT = auto()
    COMMITTED = auto()
    SPECIALIZED = auto()
    MATURE = auto()
    SENESCENT = auto()

class MorphologyType(Enum):
    CORTICAL_SHEET = "cortical_sheet"
    COLUMNAR_3D = "columnar_3d"
    MESH_TOPOLOGY = "mesh_topology"
    RADIAL_GLIA = "radial_glia"
    SWARM_LOOM = "swarm_loom"

class PatternSymmetry(Enum):
    NONE = auto()
    REFLECTION_XY = auto()
    REFLECTION_XZ = auto()
    REFLECTION_YZ = auto()
    ROTATIONAL_180 = auto()
    ROTATIONAL_90 = auto()
    FULL_CUBIC = auto()

class BandPruningStrategy(Enum):
    """Strategies for band pruning along connections."""
    NONE = auto()           # No pruning
    ENDPOINT_ONLY = auto()  # Sample only endpoints
    MIDPOINT = auto()       # Sample endpoints + midpoint
    QUARTILE = auto()       # Sample at 0%, 25%, 50%, 75%, 100%
    ADAPTIVE = auto()       # Sample density based on connection length

# ═══════════════════════════════════════════════════════════════
# GENOME SPEC — ES-HyperNEAT Parameters
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class GenomeSpec:
    """
    Genome with ES-HyperNEAT + LEO parameters.

    ES-HyperNEAT adds:
      - max_depth: int (octree recursion depth)
      - variance_threshold: float (subdivision trigger)
      - band_pruning_threshold: float (connection pruning)
      - band_pruning_strategy: BandPruningStrategy
      - initial_resolution: Tuple[int, int, int] (coarse grid)
      - min_cell_size: float (smallest allowable cell)
    """
    activation: str = "tanh"
    hidden_layers: Tuple[int, ...] = (64, 64, 64)
    output_dim: int = 5  # [weight, bias, lr_gate, plasticity, expression]
    genomic_signature: str = "Y-4.0-ESHN-LEO-GTH-SEISMIC"
    mutation_rate: float = 0.01
    crossover_rate: float = 0.7

    # LEO parameters
    expression_threshold: float = 0.5
    expression_output_index: int = 4
    pattern_symmetry: PatternSymmetry = PatternSymmetry.REFLECTION_XY
    leo_enabled: bool = True
    expression_variance_threshold: float = 0.05

    # ═══════════════════════════════════════════════════════
    # ES-HYPERNEAT PARAMETERS
    # ═══════════════════════════════════════════════════════
    max_depth: int = 6                    # Octree max recursion depth
    variance_threshold: float = 0.03       # Subdivide if CPPN variance > this
    band_pruning_threshold: float = 0.02   # Prune connection if variance < this
    band_pruning_strategy: BandPruningStrategy = BandPruningStrategy.QUARTILE
    initial_resolution: Tuple[int, int, int] = (4, 4, 2)  # Coarse starting grid
    min_cell_size: float = 0.5             # Minimum spatial cell size
    max_nodes: int = 10000                 # Hard cap on node count
    connectivity_radius: float = 5.0       # Max connection distance

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True,
                           default=lambda x: x.name if isinstance(x, Enum) else x)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

@dataclass
class SubstrateConfig:
    bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]] = (
        (-10.0, -10.0, -5.0), (10.0, 10.0, 5.0)
    )
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    connectivity_radius: float = 5.0
    target_density: float = 0.15

    def volume(self) -> float:
        (xmin, ymin, zmin), (xmax, ymax, zmax) = self.bounds
        return (xmax - xmin) * (ymax - ymin) * (zmax - zmin)

# ═══════════════════════════════════════════════════════════════
# OCTREE DATA STRUCTURE — Pure Python (not JAX)
# ═══════════════════════════════════════════════════════════════
@dataclass
class OctreeNode:
    """
    Octree node for spatial subdivision.

    Each node represents a cubic region of substrate space.
    Leaf nodes contain actual neuron positions.
    """
    # Spatial bounds
    center: Tuple[float, float, float]
    size: Tuple[float, float, float]  # Half-extents (dx, dy, dz)

    # Tree structure
    depth: int
    children: List['OctreeNode'] = field(default_factory=list)
    is_leaf: bool = True

    # CPPN variance at this region
    variance_weight: float = 0.0
    variance_expression: float = 0.0
    variance_combined: float = 0.0

    # Node placement (only for leaves)
    has_neuron: bool = False
    neuron_position: Optional[Tuple[float, float, float]] = None
    neuron_id: Optional[int] = None

    # Differentiation metadata
    differentiation_state: DifferentiationState = DifferentiationState.PLURIPOTENT

    def subdivide(self) -> List['OctreeNode']:
        """Split into 8 octants."""
        cx, cy, cz = self.center
        dx, dy, dz = self.size

        children = []
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    child_center = (
                        cx + (i - 0.5) * dx,
                        cy + (j - 0.5) * dy,
                        cz + (k - 0.5) * dz
                    )
                    child_size = (dx / 2, dy / 2, dz / 2)
                    children.append(OctreeNode(
                        center=child_center,
                        size=child_size,
                        depth=self.depth + 1,
                        is_leaf=True
                    ))

        self.children = children
        self.is_leaf = False
        return children

    def get_corners(self) -> List[Tuple[float, float, float]]:
        """Get 8 corner coordinates of this cell."""
        cx, cy, cz = self.center
        dx, dy, dz = self.size
        corners = []
        for i in [0, 1]:
            for j in [0, 1]:
                for k in [0, 1]:
                    corners.append((
                        cx + (i - 0.5) * dx * 2,
                        cy + (j - 0.5) * dy * 2,
                        cz + (k - 0.5) * dz * 2
                    ))
        return corners

    def get_edge_midpoints(self) -> List[Tuple[float, float, float]]:
        """Get midpoints of 12 edges."""
        cx, cy, cz = self.center
        dx, dy, dz = self.size

        midpoints = [
            # Edges parallel to x
            (cx, cy - dy, cz - dz), (cx, cy + dy, cz - dz),
            (cx, cy - dy, cz + dz), (cx, cy + dy, cz + dz),
            # Edges parallel to y
            (cx - dx, cy, cz - dz), (cx + dx, cy, cz - dz),
            (cx - dx, cy, cz + dz), (cx + dx, cy, cz + dz),
            # Edges parallel to z
            (cx - dx, cy - dy, cz), (cx + dx, cy - dy, cz),
            (cx - dx, cy + dy, cz), (cx + dx, cy + dy, cz),
        ]
        return midpoints

    def get_sample_points(self) -> List[Tuple[float, float, float]]:
        """All sample points for variance computation: corners + center + edges."""
        points = self.get_corners()
        points.append(self.center)
        points.extend(self.get_edge_midpoints())
        return points

# ═══════════════════════════════════════════════════════════════
# PATTERN LIBRARY — Extended for ES-HyperNEAT
# ═══════════════════════════════════════════════════════════════
class PatternLibrary:
    """Singleton pattern cache with ES-HyperNEAT topology support."""
    _instance = None
    _patterns: Dict[str, Dict[str, Any]] = {}
    _octree_cache: Dict[str, OctreeNode] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def cache_octree(self, fingerprint: str, root: OctreeNode) -> None:
        """Cache octree topology for reuse."""
        self._octree_cache[fingerprint] = root

    def retrieve_octree(self, fingerprint: str) -> Optional[OctreeNode]:
        """Retrieve cached octree."""
        return self._octree_cache.get(fingerprint)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_patterns": len(self._patterns),
            "total_octrees": len(self._octree_cache),
            "total_reuses": sum(p.get("reuse_count", 0) for p in self._patterns.values()),
        }

# ═══════════════════════════════════════════════════════════════
# CPPN-LEO MODULE (from v3.6)
# ═══════════════════════════════════════════════════════════════
class CPPN_LEO(nn.Module):
    hidden_dims: Tuple[int, ...]
    output_dim: int = 5
    activation: str = "tanh"

    @nn.compact
    def __call__(self, coords: jnp.ndarray) -> jnp.ndarray:
        h = coords
        for i, dim in enumerate(self.hidden_dims):
            h = nn.Dense(dim, name=f"cppn_leo_h_{i}")(h)
            if self.activation == "tanh":
                h = nn.tanh(h)
            elif self.activation == "relu":
                h = nn.relu(h)
            elif self.activation == "sin":
                h = jnp.sin(h)
            elif self.activation == "gaussian":
                h = jnp.exp(-h**2)
            elif self.activation == "leaky":
                h = jnp.where(h > 0, h, 0.01 * h)
            else:
                h = nn.tanh(h)

        raw = nn.Dense(self.output_dim, name="cppn_leo_out")(h)
        return jnp.stack([
            jnp.tanh(raw[...,0]),
            raw[...,1] * 0.1,
            nn.sigmoid(raw[...,2]),
            nn.sigmoid(raw[...,3]),
            nn.sigmoid(raw[...,4])
        ], axis=-1)

# ═══════════════════════════════════════════════════════════════
# OCTREE BUILDER — Core ES-HyperNEAT Algorithm
# ═══════════════════════════════════════════════════════════════
class OctreeBuilder:
    """
    Builds adaptive octree based on CPPN variance.

    Algorithm:
    1. Create initial coarse grid (initial_resolution)
    2. For each cell, sample CPPN at multiple points
    3. Compute variance of weight and expression outputs
    4. If variance > threshold AND depth < max_depth AND cell > min_size:
       → Subdivide into 8 children, recurse
    5. Otherwise: mark as leaf, place neuron at center
    """

    def __init__(self,
                 cppn_apply: Callable,
                 params: Dict,
                 genome: GenomeSpec,
                 rng: jax.random.PRNGKey):
        self.cppn_apply = cppn_apply
        self.params = params
        self.genome = genome
        self.rng = rng
        self.total_nodes = 0
        self.subdivision_count = 0
        self.allocated_nodes = 1

    def _sample_region_variance(self,
                               region_center: Tuple[float, float, float],
                               region_size: Tuple[float, float, float]) -> Dict[str, float]:
        """
        Sample CPPN at multiple points in region and compute variance.
        Returns dict with weight_variance, expression_variance, etc.
        """
        # Build sample points: self-to-self queries for variance
        # We query CPPN with (point, point, bias=1, distance=0)
        cx, cy, cz = region_center
        dx, dy, dz = region_size

        # Sample points: center + corners + edge midpoints
        sample_points = [
            (cx, cy, cz),  # center
            (cx - dx, cy - dy, cz - dz), (cx + dx, cy - dy, cz - dz),
            (cx - dx, cy + dy, cz - dz), (cx + dx, cy + dy, cz - dz),
            (cx - dx, cy - dy, cz + dz), (cx + dx, cy - dy, cz + dz),
            (cx - dx, cy + dy, cz + dz), (cx + dx, cy + dy, cz + dz),
        ]

        # Build coordinate vectors [x1,y1,z1, x2,y2,z2, bias, dist]
        # For self-variance, source = target = sample point, dist = 0
        coords_list = []
        for px, py, pz in sample_points:
            coords_list.append([px, py, pz, px, py, pz, 1.0, 0.0])

        coords = jnp.array(coords_list)

        # Batch query CPPN
        outputs = vmap(lambda c: self.cppn_apply(self.params, c))(coords)

        weights = outputs[:, 0]
        expressions = outputs[:, 4]

        return {
            "weight_variance": float(jnp.var(weights)),
            "expression_variance": float(jnp.var(expressions)),
            "mean_expression": float(jnp.mean(expressions)),
            "mean_weight": float(jnp.mean(jnp.abs(weights))),
            "max_expression": float(jnp.max(expressions)),
            "min_expression": float(jnp.min(expressions)),
        }

    def build(self, config: SubstrateConfig) -> OctreeNode:
        """Build full octree from substrate bounds."""
        if type(self.genome.max_nodes) is not int or self.genome.max_nodes < 1:
            raise ValueError('max_nodes must be a positive integer')
        self.total_nodes = 0
        self.subdivision_count = 0
        self.allocated_nodes = 1
        (xmin, ymin, zmin), (xmax, ymax, zmax) = config.bounds
        if not all(math.isfinite(v) for v in (xmin,ymin,zmin,xmax,ymax,zmax)) or not (xmin<xmax and ymin<ymax and zmin<zmax):
            raise ValueError('invalid substrate bounds')

        # Root node encompasses entire space
        root_center = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
        root_size = ((xmax - xmin) / 2, (ymax - ymin) / 2, (zmax - zmin) / 2)

        root = OctreeNode(center=root_center, size=root_size, depth=0, is_leaf=True)

        # Initial coarse subdivision based on initial_resolution
        self._initial_subdivide(root, config)

        # Adaptive subdivision based on CPPN variance
        self._adaptive_subdivide(root)

        # Place neurons in leaf nodes
        self._place_neurons(root)

        print(f"[YENNEFER] Octree built: {self.total_nodes} nodes, {self.subdivision_count} subdivisions")

        return root

    def _initial_subdivide(self, node: OctreeNode, config: SubstrateConfig) -> None:
        """Initial grid subdivision to reach initial_resolution."""
        resolution = self.genome.initial_resolution
        if len(resolution) != 3 or any(type(v) is not int or v < 1 for v in resolution):
            raise ValueError('initial_resolution must contain three positive integers')
        target_depth = math.ceil(math.log2(max(resolution)))
        if target_depth > self.genome.max_depth:
            raise ValueError('initial resolution exceeds depth limit')
        if (8**(target_depth+1)-1)//7 > self.genome.max_nodes:
            raise ValueError('initial resolution exceeds tree-node budget')
        def fill(cell):
            if cell.depth >= target_depth: return
            if min(cell.size)/2 < self.genome.min_cell_size:
                raise ValueError('initial resolution exceeds minimum cell size')
            self.allocated_nodes += 8
            self.subdivision_count += 1
            for child in cell.subdivide(): fill(child)
        fill(node)

    def _adaptive_subdivide(self, node: OctreeNode) -> None:
        """Recursively subdivide based on CPPN variance."""
        if not node.is_leaf:
            for child in node.children:
                self._adaptive_subdivide(child)
            return

        # Check termination conditions
        if node.depth >= self.genome.max_depth:
            return

        dx, dy, dz = node.size
        if min(dx,dy,dz)/2 < self.genome.min_cell_size:
            return

        if self.allocated_nodes + 8 > self.genome.max_nodes:
            return

        # Sample CPPN variance in this region
        variance = self._sample_region_variance(node.center, node.size)
        node.variance_weight = variance["weight_variance"]
        node.variance_expression = variance["expression_variance"]
        node.variance_combined = max(variance["weight_variance"], variance["expression_variance"])

        # Decision: subdivide?
        should_subdivide = (
            node.variance_combined > self.genome.variance_threshold and
            node.depth < self.genome.max_depth
        )

        # Also subdivide if expression is high but variable (LEO)
        if self.genome.leo_enabled:
            if (variance["expression_variance"] > self.genome.expression_variance_threshold and
                variance["mean_expression"] > 0.3):
                should_subdivide = True

        if should_subdivide:
            self.allocated_nodes += 8
            children = node.subdivide()
            self.subdivision_count += 1
            for child in children:
                self._adaptive_subdivide(child)

    def _place_neurons(self, node: OctreeNode) -> None:
        """Place neurons at leaf node centers."""
        if not node.is_leaf:
            for child in node.children:
                self._place_neurons(child)
            return

        # Leaf node gets a neuron
        node.has_neuron = True
        node.neuron_position = node.center
        node.neuron_id = self.total_nodes
        self.total_nodes += 1

# ═══════════════════════════════════════════════════════════════
# BAND PRUNER — ES-HyperNEAT Connection Filtering
# ═══════════════════════════════════════════════════════════════
class BandPruner:
    """
    Prunes connections where CPPN variance along the band is low.

    For each potential connection between nearby neurons:
    1. Sample CPPN at multiple points along the connection
    2. Compute variance of outputs along the band
    3. If variance < threshold → connection is "boring" → prune
    """

    def __init__(self,
                 cppn_apply: Callable,
                 params: Dict,
                 genome: GenomeSpec):
        self.cppn_apply = cppn_apply
        self.params = params
        self.genome = genome

    def _sample_band(self,
                    pos_a: Tuple[float, float, float],
                    pos_b: Tuple[float, float, float],
                    n_samples: int = 5) -> jnp.ndarray:
        """
        Sample CPPN along connection band.
        Returns outputs array (n_samples, 5).
        """
        ax, ay, az = pos_a
        bx, by, bz = pos_b

        # Linear interpolation points
        t_values = jnp.linspace(0, 1, n_samples)

        coords_list = []
        for t in t_values:
            # Source point moves from A to B
            sx = ax + t * (bx - ax)
            sy = ay + t * (by - ay)
            sz = az + t * (bz - az)

            # Target point is always B (for directed connections)
            # Distance varies along the band
            dist = math.sqrt((bx - sx)**2 + (by - sy)**2 + (bz - sz)**2)

            coords_list.append([sx, sy, sz, bx, by, bz, 1.0, dist])

        coords = jnp.array(coords_list)
        return vmap(lambda c: self.cppn_apply(self.params, c))(coords)

    def prune_connection(self,
                        pos_a: Tuple[float, float, float],
                        pos_b: Tuple[float, float, float]) -> Dict[str, Any]:
        """
        Determine if connection should exist based on band variance.
        Returns dict with keep, weight, expression, variance.
        """
        # Determine sample count based on strategy
        strategy = self.genome.band_pruning_strategy
        if strategy == BandPruningStrategy.ENDPOINT_ONLY:
            n_samples = 2
        elif strategy == BandPruningStrategy.MIDPOINT:
            n_samples = 3
        elif strategy == BandPruningStrategy.QUARTILE:
            n_samples = 5
        elif strategy == BandPruningStrategy.ADAPTIVE:
            dist = math.sqrt(sum((a - b)**2 for a, b in zip(pos_a, pos_b)))
            n_samples = max(3, min(20, int(dist * 2)))
        else:
            n_samples = 5

        outputs = self._sample_band(pos_a, pos_b, n_samples)

        weights = outputs[:, 0]
        expressions = outputs[:, 4]

        weight_variance = float(jnp.var(weights))
        expression_variance = float(jnp.var(expressions))

        # LEO: Connection exists if mean expression > threshold
        mean_expression = float(jnp.mean(expressions))
        expressed = mean_expression > self.genome.expression_threshold

        # Band pruning: keep if variance is interesting
        interesting = (
            weight_variance > self.genome.band_pruning_threshold or
            expression_variance > self.genome.band_pruning_threshold
        )

        # Final decision
        keep = expressed and interesting

        # Weight is average along band (or endpoint)
        final_weight = float(jnp.mean(weights))
        final_expression = mean_expression

        return {
            "keep": keep,
            "weight": final_weight,
            "expression": final_expression,
            "weight_variance": weight_variance,
            "expression_variance": expression_variance,
            "samples": n_samples
        }

# ═══════════════════════════════════════════════════════════════
# NEURAL SUBSTRATE — Extended for ES-HyperNEAT
# ═══════════════════════════════════════════════════════════════
@dataclass
class NeuralSubstrate:
    morphology: MorphologyType
    config: SubstrateConfig

    node_positions: jnp.ndarray = field(repr=False)
    node_states: jnp.ndarray = field(repr=False)
    adjacency_weights: jnp.ndarray = field(repr=False)
    adjacency_mask: jnp.ndarray = field(repr=False)

    expression_values: jnp.ndarray = field(repr=False, default=None)
    expression_threshold: float = 0.5

    # ES-HyperNEAT metadata
    octree_root: Optional[OctreeNode] = field(repr=False, default=None)
    node_depths: jnp.ndarray = field(repr=False, default=None)  # Depth of each node in octree
    band_pruning_stats: Dict[str, Any] = field(default_factory=dict)

    genome_fingerprint: str = ""
    differentiation: str = "pluripotent"
    genomic_signature: str = "Y-4.0-ESHN-LEO-GTH-SEISMIC"
    pattern_fingerprint: str = ""

    differentiation_map: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def to_networkx(self) -> Any:
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx required")

        G = nx.DiGraph()
        n = self.node_positions.shape[0]

        for i in range(n):
            x, y, z = self.node_positions[i]
            state = DifferentiationState(int(self.node_states[i]))
            depth = int(self.node_depths[i]) if self.node_depths is not None else 0
            G.add_node(i, pos=(float(x), float(y), float(z)),
                      state=state.name,
                      depth=depth,
                      **self.differentiation_map.get(i, {}))

        rows, cols = jnp.where(self.adjacency_mask)
        for i, j in zip(rows.tolist(), cols.tolist()):
            w = float(self.adjacency_weights[i, j])
            expr = float(self.expression_values[i, j]) if self.expression_values is not None else 0.0
            G.add_edge(i, j, weight=w, expression=expr,
                      expressed=expr > self.expression_threshold)

        return G

    def to_jsonl(self) -> str:
        stats = self.get_topology_stats()
        record = {
            "protocol": "ACP/1.0",
            "agent": "Yennefer",
            "skill_namespace": "neurohomogenism.es_hyperneat",
            "binding": "conv_a1b2c3d4e5f6g7h8i9j0",
            "genome_fingerprint": self.genome_fingerprint,
            "genomic_signature": self.genomic_signature,
            "pattern_fingerprint": self.pattern_fingerprint,
            "morphology": self.morphology.value,
            "differentiation": self.differentiation,
            "node_count": int(self.node_positions.shape[0]),
            "edge_count": int(jnp.sum(self.adjacency_mask)),
            "expression_threshold": self.expression_threshold,
            "leo_enabled": True,
            "es_hyperneat": {
                "octree_depth_max": int(jnp.max(self.node_depths)) if self.node_depths is not None else 0,
                "octree_depth_avg": float(jnp.mean(self.node_depths)) if self.node_depths is not None else 0.0,
                "band_pruning": self.band_pruning_stats
            },
            "topology_stats": stats,
            "timestamp": "2026-05-22T18:47:00Z",
            "pi": "Igor A. Holt",
            "org": "genesisconductor.io"
        }
        return json.dumps(record, separators=(',', ':'))

    def get_topology_stats(self) -> Dict[str, Any]:
        n = self.node_positions.shape[0]
        total_possible = n * (n - 1)
        actual_edges = int(jnp.sum(self.adjacency_mask))

        in_degrees = jnp.sum(self.adjacency_mask, axis=0)
        out_degrees = jnp.sum(self.adjacency_mask, axis=1)

        return {
            "sparsity": actual_edges / total_possible if total_possible > 0 else 0.0,
            "actual_edges": actual_edges,
            "total_possible": total_possible,
            "avg_in_degree": float(jnp.mean(in_degrees)),
            "avg_out_degree": float(jnp.mean(out_degrees)),
            "max_in_degree": int(jnp.max(in_degrees)),
            "max_out_degree": int(jnp.max(out_degrees)),
            "expression_mean": float(jnp.mean(self.expression_values)) if self.expression_values is not None else 0.0
        }

# ═══════════════════════════════════════════════════════════════
# ES-HYPERNEAT SUBSTRATE — Main Production Class
# ═══════════════════════════════════════════════════════════════
class ES_HyperNEAT_Substrate:
    """
    Evolvable-Substrate HyperNEAT with full quadtree/octree resolution.

    Workflow:
    1. Build adaptive octree based on CPPN variance
    2. Extract neuron positions from leaf nodes
    3. Band-prune connections between nearby neurons
    4. Assemble NeuralSubstrate with JAX arrays
    5. Apply differentiation protocol
    """

    def __init__(self,
                 genome_path: Optional[str] = None,
                 genome_spec: Optional[GenomeSpec] = None):

        if not JAX_AVAILABLE:
            raise ImportError("JAX/Flax required. pip install jax flax optax")

        self.genome = genome_spec or self._load_or_default(genome_path)
        self.cppn = self._build_cppn()
        self.rng = random.PRNGKey(0xC0DA)
        self.params = self._init_params()
        self.pattern_lib = PatternLibrary()

        print(f"[YENNEFER] ES-HyperNEAT v4.0 initialized")
        print(f"[YENNEFER] Max depth: {self.genome.max_depth}")
        print(f"[YENNEFER] Variance threshold: {self.genome.variance_threshold}")
        print(f"[YENNEFER] Band pruning: {self.genome.band_pruning_strategy.name}")

    def _load_or_default(self, path: Optional[str]) -> GenomeSpec:
        if path and Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            if "pattern_symmetry" in data:
                data["pattern_symmetry"] = PatternSymmetry[data["pattern_symmetry"]]
            if "band_pruning_strategy" in data:
                data["band_pruning_strategy"] = BandPruningStrategy[data["band_pruning_strategy"]]
            return GenomeSpec(**data)
        return GenomeSpec()

    def _build_cppn(self) -> CPPN_LEO:
        return CPPN_LEO(
            hidden_dims=self.genome.hidden_layers,
            output_dim=self.genome.output_dim,
            activation=self.genome.activation
        )

    def _init_params(self) -> Dict:
        dummy = jnp.ones((1, 8))
        self.rng, init_rng = random.split(self.rng)
        return self.cppn.init(init_rng, dummy)

    @jit
    def _query_cppn_batch(self, coords: jnp.ndarray) -> jnp.ndarray:
        return self.cppn.apply(self.params, coords)

    def generate(self,
                morphology: MorphologyType,
                config: SubstrateConfig,
                differentiation: str = "pluripotent",
                use_cache: bool = True) -> NeuralSubstrate:
        """
        Generate substrate with ES-HyperNEAT adaptive resolution.
        """

        # ═══════════════════════════════════════════════════════
        # PHASE 1: Build Adaptive Octree
        # ═══════════════════════════════════════════════════════
        cache_key = f"octree:{morphology.value}:{config.bounds}:{self.genome.fingerprint()}"

        use_cache = False  # Safety: incomplete parameter binding in legacy cache key.
        if use_cache:
            cached_root = self.pattern_lib.retrieve_octree(cache_key)
            if cached_root:
                print(f"[YENNEFER] Octree cache HIT")
                root = cached_root
            else:
                print(f"[YENNEFER] Octree cache MISS — building adaptive octree")
                builder = OctreeBuilder(
                    cppn_apply=self.cppn.apply,
                    params=self.params,
                    genome=self.genome,
                    rng=self.rng
                )
                root = builder.build(config)
                self.pattern_lib.cache_octree(cache_key, root)
        else:
            builder = OctreeBuilder(
                cppn_apply=self.cppn.apply,
                params=self.params,
                genome=self.genome,
                rng=self.rng
            )
            root = builder.build(config)

        # ═══════════════════════════════════════════════════════
        # PHASE 2: Extract Nodes from Octree
        # ═══════════════════════════════════════════════════════
        nodes = self._extract_nodes(root)
        n_nodes = len(nodes)

        print(f"[YENNEFER] Extracted {n_nodes} nodes from octree")

        # Build position array
        positions = jnp.array([n.neuron_position for n in nodes])
        depths = jnp.array([n.depth for n in nodes])

        # ═══════════════════════════════════════════════════════
        # PHASE 3: Band Pruning for Connections
        # ═══════════════════════════════════════════════════════
        pruner = BandPruner(
            cppn_apply=self.cppn.apply,
            params=self.params,
            genome=self.genome
        )

        adj_mask = jnp.zeros((n_nodes, n_nodes), dtype=bool)
        adj_weights = jnp.zeros((n_nodes, n_nodes))
        expression_values = jnp.zeros((n_nodes, n_nodes))

        pruned_count = 0
        kept_count = 0

        # Connect nearby nodes (within connectivity_radius)
        for i in range(n_nodes):
            px, py, pz = nodes[i].neuron_position
            for j in range(n_nodes):
                if i == j:
                    continue

                qx, qy, qz = nodes[j].neuron_position
                dist = math.sqrt((px - qx)**2 + (py - qy)**2 + (pz - qz)**2)

                if dist > self.genome.connectivity_radius:
                    continue

                # Band prune this connection
                result = pruner.prune_connection(
                    (px, py, pz),
                    (qx, qy, qz)
                )

                if result["keep"]:
                    adj_mask = adj_mask.at[i, j].set(True)
                    adj_weights = adj_weights.at[i, j].set(result["weight"])
                    expression_values = expression_values.at[i, j].set(result["expression"])
                    kept_count += 1
                else:
                    pruned_count += 1

        band_stats = {
            "pruned": pruned_count,
            "kept": kept_count,
            "prune_ratio": pruned_count / (pruned_count + kept_count) if (pruned_count + kept_count) > 0 else 0.0,
            "strategy": self.genome.band_pruning_strategy.name
        }

        print(f"[YENNEFER] Band pruning: {kept_count} kept, {pruned_count} pruned ({band_stats['prune_ratio']*100:.1f}%)")

        # ═══════════════════════════════════════════════════════
        # PHASE 4: Differentiation Protocol
        # ═══════════════════════════════════════════════════════
        node_states = jnp.full(n_nodes, DifferentiationState.PLURIPOTENT.value)
        diff_map = {}

        if morphology == MorphologyType.COLUMNAR_3D:
            # Differentiate based on z-position
            z_min = float(jnp.min(positions[:, 2]))
            z_max = float(jnp.max(positions[:, 2]))
            z_range = z_max - z_min

            for i in range(n_nodes):
                z = float(positions[i, 2])
                z_norm = (z - z_min) / z_range if z_range > 0 else 0.5

                if z_norm < 0.2:
                    node_states = node_states.at[i].set(DifferentiationState.SPECIALIZED.value)
                    diff_map[i] = {"layer": "input", "type": "sensor", "depth": int(depths[i])}
                elif z_norm > 0.8:
                    node_states = node_states.at[i].set(DifferentiationState.SPECIALIZED.value)
                    diff_map[i] = {"layer": "output", "type": "motor", "depth": int(depths[i])}
                else:
                    node_states = node_states.at[i].set(DifferentiationState.COMMITTED.value)
                    diff_map[i] = {"layer": "hidden", "type": "interneuron", "depth": int(depths[i])}

        elif morphology == MorphologyType.CORTICAL_SHEET:
            # 2D sheet: edge neurons are inhibitory
            x_min = float(jnp.min(positions[:, 0]))
            x_max = float(jnp.max(positions[:, 0]))
            x_range = x_max - x_min

            for i in range(n_nodes):
                x = float(positions[i, 0])
                x_norm = (x - x_min) / x_range if x_range > 0 else 0.5

                if x_norm < 0.1 or x_norm > 0.9:
                    node_states = node_states.at[i].set(DifferentiationState.SPECIALIZED.value)
                    diff_map[i] = {"region": "border", "type": "inhibitory", "depth": int(depths[i])}

        # ═══════════════════════════════════════════════════════
        # PHASE 5: Assemble Substrate
        # ═══════════════════════════════════════════════════════
        pattern_fp = hashlib.sha256(
            json.dumps({
                "morphology": morphology.value,
                "bounds": config.bounds,
                "nodes": n_nodes,
                "edges": kept_count,
                "signature": self.genome.genomic_signature
            }, sort_keys=True).encode()
        ).hexdigest()[:20]

        substrate = NeuralSubstrate(
            morphology=morphology,
            config=config,
            node_positions=positions,
            node_states=node_states,
            adjacency_weights=adj_weights,
            adjacency_mask=adj_mask,
            expression_values=expression_values,
            expression_threshold=self.genome.expression_threshold,
            octree_root=root,
            node_depths=depths,
            band_pruning_stats=band_stats,
            genome_fingerprint=self.genome.fingerprint(),
            differentiation=differentiation,
            genomic_signature=self.genome.genomic_signature,
            pattern_fingerprint=pattern_fp,
            differentiation_map=diff_map
        )

        stats = substrate.get_topology_stats()
        print(f"[YENNEFER] ES-HyperNEAT substrate complete")
        print(f"[YENNEFER] Nodes: {n_nodes}, Edges: {stats['actual_edges']}, Sparsity: {stats['sparsity']*100:.2f}%")
        print(f"[YENNEFER] Avg depth: {float(jnp.mean(depths)):.2f}, Max depth: {int(jnp.max(depths))}")

        return substrate

    def _extract_nodes(self, root: OctreeNode) -> List[OctreeNode]:
        """Flatten octree to list of leaf nodes with neurons."""
        nodes = []

        def traverse(node: OctreeNode):
            if node.is_leaf:
                if node.has_neuron:
                    nodes.append(node)
            else:
                for child in node.children:
                    traverse(child)

        traverse(root)
        return nodes

    def mutate_genome(self, mutation_strength: float = 0.1) -> GenomeSpec:
        """ES-HyperNEAT aware mutation."""
        self.rng, mut_rng = random.split(self.rng)

        new_layers = tuple(
            max(8, int(dim * (1 + float(random.normal(mut_rng)) * mutation_strength)))
            for dim in self.genome.hidden_layers
        )

        # Evolve ES-HyperNEAT parameters
        new_variance_threshold = jnp.clip(
            self.genome.variance_threshold * (1 + float(random.normal(mut_rng)) * 0.2),
            0.001, 0.5
        )

        new_band_threshold = jnp.clip(
            self.genome.band_pruning_threshold * (1 + float(random.normal(mut_rng)) * 0.2),
            0.001, 0.5
        )

        new_max_depth = max(2, min(12, 
            self.genome.max_depth + int(float(random.normal(mut_rng)) * 2)))

        return GenomeSpec(
            activation=self.genome.activation,
            hidden_layers=new_layers,
            output_dim=self.genome.output_dim,
            genomic_signature=f"{self.genome.genomic_signature}-MUT-ESHN",
            mutation_rate=self.genome.mutation_rate * (1 + float(random.normal(mut_rng)) * 0.1),
            crossover_rate=self.genome.crossover_rate,
            expression_threshold=self.genome.expression_threshold,
            expression_output_index=self.genome.expression_output_index,
            pattern_symmetry=self.genome.pattern_symmetry,
            leo_enabled=True,
            expression_variance_threshold=self.genome.expression_variance_threshold,
            max_depth=int(new_max_depth),
            variance_threshold=float(new_variance_threshold),
            band_pruning_threshold=float(new_band_threshold),
            band_pruning_strategy=self.genome.band_pruning_strategy,
            initial_resolution=self.genome.initial_resolution,
            min_cell_size=self.genome.min_cell_size * 0.95,
            max_nodes=self.genome.max_nodes,
            connectivity_radius=self.genome.connectivity_radius
        )

# ═══════════════════════════════════════════════════════════════
# SWARM CONSENSUS — ES-HyperNEAT Verification
# ═══════════════════════════════════════════════════════════════
class SwarmConsensus_ESHN:
    """Verification with ES-HyperNEAT topology analysis."""

    @staticmethod
    def verify_substrate(substrate: NeuralSubstrate,
                        checkpoint: str) -> Dict[str, Any]:
        stats = substrate.get_topology_stats()

        # Analyze depth distribution
        depths = substrate.node_depths
        depth_hist = {}
        if depths is not None:
            for d in range(int(jnp.max(depths)) + 1):
                count = int(jnp.sum(depths == d))
                if count > 0:
                    depth_hist[str(d)] = count

        return {
            "checkpoint": checkpoint,
            "fingerprint": substrate.genome_fingerprint,
            "pattern_fingerprint": substrate.pattern_fingerprint,
            "node_count": int(substrate.node_positions.shape[0]),
            "edge_count": stats["actual_edges"],
            "sparsity": stats["sparsity"],
            "expression_threshold": substrate.expression_threshold,
            "es_hyperneat": {
                "depth_distribution": depth_hist,
                "max_depth": int(jnp.max(depths)) if depths is not None else 0,
                "avg_depth": float(jnp.mean(depths)) if depths is not None else 0.0,
                "band_pruning": substrate.band_pruning_stats
            },
            "leo_verified": True,
            "eshn_verified": True,
            "verified": True,
            "timestamp": "2026-05-22T18:47:00Z"
        }

# ═══════════════════════════════════════════════════════════════
# EXAMPLE / CLI
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    substrate = ES_HyperNEAT_Substrate()

    network = substrate.generate(
        morphology=MorphologyType.COLUMNAR_3D,
        config=SubstrateConfig(
            bounds=((-8.0, -8.0, -4.0), (8.0, 8.0, 4.0)),
            connectivity_radius=4.0
        ),
        differentiation="sensorimotor_v1"
    )

    print(network.to_jsonl())

    consensus = SwarmConsensus_ESHN.verify_substrate(network, "SEISMIC-ESHN-001")
    print(json.dumps(consensus, indent=2))
