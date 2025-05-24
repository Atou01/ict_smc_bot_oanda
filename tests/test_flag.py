import importlib, sys, types, argparse, pytest, os

# Ajout du chemin pour l'importation depuis src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_flag_activation(monkeypatch):
    # Créer un mock du module llm_engine
    mock_llm = types.ModuleType("llm_engine")
    mock_llm.decide_trade = lambda x: {"status": "mocked"}
    monkeypatch.setitem(sys.modules, "src.bot.llm_engine", mock_llm)
    
    # Importer main après le monkey patch
    from src.bot import main
    
    # Tester le comportement du parser d'arguments
    parser = main.build_arg_parser() if hasattr(main, 'build_arg_parser') else argparse.ArgumentParser()
    if not hasattr(parser, 'parse_args'):
        pytest.skip("Parser d'arguments non disponible dans main.py")
    
    # Vérifier sans le flag
    args = parser.parse_args([])
    assert not getattr(args, 'use_llm_v1', False)
    
    # Vérifier avec le flag
    args = parser.parse_args(["--use-llm-v1"])
    assert getattr(args, 'use_llm_v1', False)
    
    # Vérifier la fonction should_use_llm si elle existe
    if hasattr(main, 'should_use_llm'):
        assert not main.should_use_llm(args_without_flag)
        assert main.should_use_llm(args_with_flag)
