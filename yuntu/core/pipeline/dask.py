"""Base class for dask pipeline."""
import os
from dask.threaded import get
import dask.dataframe as dd
from dask.optimization import cull, inline, inline_functions, fuse
from yuntu.core.pipeline.base import Pipeline
from yuntu.core.pipeline.nodes.inputs import DictInput

DASK_CONFIG = {'npartitions': 1}


class DaskPipeline(Pipeline):
    """Pipeline that uses dask as a parallel processing manager."""

    def __init__(self,
                 *args,
                 work_dir=None,
                 **kwargs):
        super().__init__(*args, *kwargs)
        if work_dir is None:
            work_dir = "/tmp"
        if not os.path.isdir(work_dir):
            message = "Argument 'work_dir' must be a valid directory."
            raise ValueError(message)
        self.work_dir = work_dir
        self.graph = {}
        self.init_pipeline()

    def init_pipeline(self):
        """Initialize pipeline."""
        base_dir = os.path.join(self.work_dir, self.name)
        persist_dir = os.path.join(base_dir, 'persist')
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        if not os.path.exists(persist_dir):
            os.mkdir(persist_dir)

    def build(self):
        """Add operations that are specific to each pipeline."""

    def _add_operation(self,
                       name,
                       operation,
                       inputs=None,
                       is_output=False,
                       persist=False):
        """Add operation."""
        if not isinstance(name, str):
            message = "Argument 'name' must be a string."
            raise ValueError(message)
        if not hasattr(operation, '__call__'):
            message = "Argument 'operation' must be a callable object."
            raise ValueError(message)
        if inputs is not None:
            if not isinstance(inputs, (tuple, list)):
                message = "Argument 'inputs' must be a list or a tuple" + \
                          " of node names."
                raise ValueError(message)
            self.graph[name] = (operation, *inputs)
        else:
            self.graph[name] = (operation,)

        if is_output:
            self._mark_output(name)
        elif persist:
            self._mark_persist(name)

    def _add_input(self, name, data):
        """Add input."""
        if not isinstance(name, str):
            message = "Argument 'name' must be a string."
            raise ValueError(message)
        if data is None:
            message = "Argument 'data' can not be undefined."
            raise ValueError(message)
        self.graph[name] = data

    def write_node(self, name, result):
        """Persist computations as files."""
        if self.node_exists(name):
            return self.nodes[name].write()
        raise ValueError("Node does not exist.")

    def read_node(self, name):
        """Read persisted node."""
        if self.node_exists(name):
            return self.nodes[name].read()
        raise ValueError("Node does not exist.")

    def clear_persisted(self, name):
        """Delete persisted node."""
        if self.node_exists(name):
            return self.nodes[name].clear()
        raise ValueError("Node does not exist.")

    def clear(self):
        """Clear all persisted information."""
        for name in self.persist:
            self.clear_persisted(name)

    def rebuild(self):
        """Cear all data and rebuild."""
        self.clear()
        self.graph = {}
        self.inputs = {}
        self.operations = {}
        self.persist = []
        self.outputs = []
        self.build()

    def get_nodes(self, names, client=None, compute=False, force=False):
        for name in names:
            print(self.nodes.keys())
            if not self.node_exists(name):
                raise ValueError('No node named '+name)

        results = {}
        to_retrieve = []

        for name in names:
            if name in self.persist:
                if not force and self.nodes[name].is_persisted():
                    node = self.nodes[name].read()
                    if compute and hasattr(self.nodes[name], 'compute'):
                        node = node.compute()
                        self.nodes[name].result = node
                    results[name] = node
                else:
                    to_retrieve.append(name)
            else:
                to_retrieve.append(name)
        if client is not None:
            retrieved = client.get(self.graph,
                                   to_retrieve,
                                   sync=False).result()
        else:
            retrieved = get(self.graph, to_retrieve)
        for i in range(len(to_retrieve)):
            node = retrieved[i]
            if compute and hasattr(node, 'compute'):
                node = node.compute()
                self.nodes[name].result = node
                if name in self.persist:
                    self.nodes[name].write()
            results[name] = node
        return results

    def get_node(self, name, client=None, compute=False, force=False):
        """Get node from pipeline graph."""
        return self.get_nodes(names=[name],
                              client=client,
                              compute=compute, force=force)[name]

    def compute(self,
                nodes=None,
                force=False,
                client=None,
                dask_config=None):
        """Compute pipeline."""
        if dask_config is None:
            dask_config = DASK_CONFIG
        DictInput("dask_config",
                  data=dask_config,
                  pipeline=self)
        if nodes is None:
            nodes = self.outputs
        if not isinstance(nodes, (tuple, list)):
            message = "Argument 'nodes' must be a tuple or a list."
            raise ValueError(message)
        return self.get_nodes(nodes, client=client, compute=True, force=force)

    def linearize_operations(self, op_names):
        """Linearize dask operations."""
        graph1, deps = cull(self.graph, op_names)
        graph2 = inline(graph1, dependencies=deps)
        graph3 = inline_functions(graph2,
                                  op_names,
                                  [len, str.split],
                                  dependencies=deps)
        graph4, deps = fuse(graph3)
        self.graph = graph4

    def __and__(self, other):
        """Disjoint parallelism operator '&'.

        Returns new pipeline with nodes from both pipelines running in disjoint
        paralellism. If node names are duplicated, subindices '0' and '1' are
        employed to indicate the origin (left and right). The resulting
        pipeline's 'work_dir' will be that of the first operand.
        """
        name = self.name + "|" + other.name
        work_dir = self.work_dir
        new_pipeline = DaskPipeline(name, work_dir=work_dir)
        node_rel = {}
        for key in self.nodes:
            if key not in node_rel:
                node_rel[key] = []
            node_rel[key].append(self.nodes[key])
        for key in other.nodes:
            if key not in node_rel:
                node_rel[key] = []
            node_rel[key].append(other.nodes[key])
        to_linearize = []
        for key in node_rel:
            if len(node_rel[key]) > 1:
                for i in range(len(node_rel[key])):
                    to_add = node_rel[key][i]
                    new_name = f"{to_add.name}_{i}"
                    new_inputs = []
                    if hasattr(to_add, 'inputs'):
                        to_linearize.append(new_name)
                        for inp in range(len(to_add.inputs)):
                            input_name = to_add.inputs[inp]
                            if len(node_rel[input_name]) > 1:
                                input_name = f"{input_name}_{i}"
                            new_inputs.append(input_name)
                        to_add.inputs = new_inputs
                    to_add.name = new_name
                    new_pipeline.add_node(to_add)
            else:
                new_pipeline.add_node(node_rel[key][0])
        new_pipeline.linearize_operations(to_linearize)
        return new_pipeline
