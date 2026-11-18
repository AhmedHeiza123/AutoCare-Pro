"""Exercise security boundaries from actual function ASTs without a live DB."""
import ast
import copy
import ipaddress
from pathlib import Path
from types import SimpleNamespace
import unittest

APP=Path(__file__).resolve().parents[1]/'app'
def load_function(file,name,namespace):
    tree=ast.parse(file.read_text(encoding='utf-8'))
    node=copy.deepcopy(next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name))
    if hasattr(node,'decorator_list'):node.decorator_list=[]
    module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node],type_ignores=[])
    exec(compile(ast.fix_missing_locations(module),str(file),'exec'),namespace)
    return namespace[name]

class PublicSecurityTests(unittest.TestCase):
    def test_remote_first_admin_setup_is_refused_before_db_access(self):
        ns={'Depends':lambda *a,**k:None,'get_db':None,'ip_address':ipaddress.ip_address}
        ns['AppError']=load_function(APP/'core/errors.py','AppError',{})
        tree=ast.parse((APP/'api/auth.py').read_text(encoding='utf-8'))
        if any(isinstance(n,ast.FunctionDef) and n.name=='_require_local_setup' for n in tree.body):
            load_function(APP/'api/auth.py','_require_local_setup',ns)
        first=load_function(APP/'api/auth.py','first_admin',ns)
        request=SimpleNamespace(client=SimpleNamespace(host='192.0.2.14'))
        with self.assertRaises(ns['AppError']) as caught:first(None,request,None)
        self.assertEqual(caught.exception.status,403)

    def test_local_setup_gate_accepts_loopback_and_rejects_unknown_clients(self):
        ns={'ip_address':ipaddress.ip_address}
        ns['AppError']=load_function(APP/'core/errors.py','AppError',{})
        tree=ast.parse((APP/'api/auth.py').read_text(encoding='utf-8'))
        self.assertTrue(any(isinstance(n,ast.FunctionDef) and n.name=='_require_local_setup' for n in tree.body),'Local setup gate missing')
        gate=load_function(APP/'api/auth.py','_require_local_setup',ns)
        for host in ('127.0.0.1','::1','::ffff:127.0.0.1'):
            gate(SimpleNamespace(client=SimpleNamespace(host=host)))
        for client in (None,SimpleNamespace(host='198.51.100.4'),SimpleNamespace(host='invalid-host')):
            with self.assertRaises(ns['AppError']):gate(SimpleNamespace(client=client))

    def test_public_restore_progress_excludes_paths_database_names_and_errors(self):
        secret='PRIVATE_TEST_DATABASE_NAME'
        ns={'restore':SimpleNamespace(read_status=lambda:{'state':'failed','steps':[{'key':'swap','label':'Swap','status':'failed','detail':secret}],'old_database':secret,'error':secret})}
        result=load_function(APP/'api/backup.py','restore_status',ns)()
        self.assertEqual(result['state'],'failed')
        self.assertEqual(result['steps'],[{'key':'swap','label':'Swap','status':'failed'}])
        self.assertIsNone(result['error'])
        self.assertNotIn(secret,str(result))

if __name__=='__main__':unittest.main()
