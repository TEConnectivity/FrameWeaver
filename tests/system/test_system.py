import pytest
import requests

# Project import
import main

@pytest.mark.usefixtures("start_system")
class TestSystem:
    def test_system_monitor(self,start_system):
        """Check that launch func launch every services"""

        assert requests.get(f'http://localhost:{main.config["input"]["http"]["port"]}/monitor').status_code == 200
        


    def test_stop_system(self,start_system):
        """Check that launch func launch every services"""

        with pytest.raises(SystemExit):
            main.shutdown(start_system)






