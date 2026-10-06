from pathlib import Path
import importlib.util

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_generator_and_benchmark_files_exist():
    assert Path("benchmarks/long_documents/generate_a31_pdf.py").exists()
    assert Path("benchmarks/long_documents/run_a31_real_pdf.py").exists()
