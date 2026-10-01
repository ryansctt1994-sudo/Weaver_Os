import unittest, runpy
m=runpy.run_path('es_hyperneat_reviewed.py',run_name='tested_module')
Genome,Config,Builder=m['GenomeSpec'],m['SubstrateConfig'],m['OctreeBuilder']
class BudgetTests(unittest.TestCase):
    def builder(self,cap,res=(1,1,1)):
        b=Builder(None,{},Genome(max_nodes=cap,max_depth=5,min_cell_size=.01,initial_resolution=res),None)
        b._sample_region_variance=lambda *_:dict(weight_variance=1,expression_variance=1,mean_expression=1)
        return b
    def count(self,node): return 1+sum(self.count(c) for c in node.children)
    def test_budget_and_repeat(self):
        for cap in [1,8,9,16,17,64,100]:
            b=self.builder(cap);tree=b.build(Config());self.assertLessEqual(self.count(tree),cap)
            self.assertEqual(self.count(tree),b.allocated_nodes)
            self.assertLessEqual(b.total_nodes,cap)
            again=b.build(Config());self.assertEqual(self.count(tree),self.count(again))
    def test_initial_resolution_budget(self):
        with self.assertRaises(ValueError): self.builder(8,(2,2,2)).build(Config())
        b=self.builder(100,(2,2,2));self.assertLessEqual(self.count(b.build(Config())),100)
    def test_bounds(self):
        with self.assertRaises(ValueError): self.builder(10).build(Config(bounds=((0,0,0),(0,1,1))))
    def test_dependency_failure_explicit(self):
        if not m['JAX_AVAILABLE']:
            with self.assertRaises(ImportError): m['ES_HyperNEAT_Substrate']()
if __name__=='__main__': unittest.main()
