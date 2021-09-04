"""Base class of all scenario objects"""

# Extended this class with some properties that should be common to scenarios from most of the solutions.
# OceanScenario subclasses this, adding extra properties.
from dataclasses import dataclass, field
import datetime

@dataclass
class NewScenario:
    # Required (no defaults):
    scenario_timestamp : datetime
    scenario_description : str
    
    # PDS Adoption Scenario Name, also acts as a key into the dictionary of pds scenarios (from custom_pds_adoption.json).
    pds_scenario_name : str

    # Conventional Solution
    conv_first_cost : float = field(default=0.0, metadata={'Units':  'US$2014/ha'})
    conv_operating_cost :  float = field(default=0.0, metadata={'Units':  'US$2014/ha/year'})
    conv_net_profit_margin :  float = field(default=0.0, metadata={'Units':  'US$2014/ha/year'})
    conv_expected_lifetime :  float = field(default=0.0, metadata={'Units':  'years'})

    # pds Solution
    soln_first_cost : float = field(default=0.0, metadata={'Units':  'US$2014/ha'})
    soln_operating_cost :  float = field(default=0.0, metadata={'Units':  'US$2014/ha/year'})
    soln_net_profit_margin :  float = field(default=0.0, metadata={'Units':  'US$2014/ha/year'})
    soln_expected_lifetime :  float = field(default=0.0, metadata={'Units':  'years'})

    # General:
    npv_discount_rate :  float = field(default=0.1, metadata={'Units':  'percentage'})

    disturbance_rate : float = field(default= 0.0, metadata={'Units': 'Percent, annually'})
    