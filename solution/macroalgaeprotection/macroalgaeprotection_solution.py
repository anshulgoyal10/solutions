
import os
import json
import pandas as pd
import numpy as np

from model.ocean_solution import OceanSolution
from model.new_unit_adoption import NewUnitAdoption
from solution.macroalgaeprotection.macroalgaeprotection_scenario import MacroalgaeProtectionScenario

class MacroalgaeProtectionSolution(OceanSolution):
    """ All calculations for Macroalgae protection currently implemented in the OceanSolution base class.
    """

    # Initialize from configuration file:
    def __init__(self, configuration_file_name = None):
        """
            Constructor requires a configuration file named 'macroalgaeprotection_solution_config.yaml'.
            This should be located in the same directory as the 'macroalgaeprotection_solution.py' module

        """

        if configuration_file_name is None:
            filename = os.path.basename(__file__)
            filename = filename.split('.')[0]
            configuration_file_name = os.path.join(os.path.dirname(__file__), filename + '_config.yaml')
        
        if not os.path.isfile(configuration_file_name):
            raise ValueError(f'Unable to find configuration file {configuration_file_name}.')

        super().__init__(configuration_file_name)
        
        # Now set macroalgaeprotection-specific config values:
        self.total_area = self._config['TotalArea']
        self.total_area_as_of_period = self._config['TotalAreaAsOfPeriod']
        self.change_per_period = self._config['ChangePerPeriod']
        
        self.delay_impact_of_protection_by_one_year= self._config['DelayImpactOfProtectionByOneYear']
        self.delay_regrowth_of_degraded_land_by_one_year= self._config['DelayRegrowthOfDegradedLandByOneYear']

    def set_up_tam(self, unit_adoption: NewUnitAdoption) -> None:
        # This should produce a flat line with y = constant = self.total_area
        unit_adoption.set_area_units_linear(total_area= self.total_area, change_per_period= self.change_per_period, total_area_as_of_period= self.total_area_as_of_period)
        unit_adoption.apply_clip(lower= None, upper= self.total_area)
        unit_adoption.apply_linear_regression()
        #unit_adoption.tam_build_cumulative_unprotected_area(self.new_growth_harvested_every)


    def load_scenario(self, scenario_name: str) -> None:

        input_stream = open(self.scenarios_file, 'r')
        scen_dict = json.load(input_stream)

        if scenario_name not in scen_dict.keys():
            raise ValueError(f"Unable to find {scenario_name} in scenario file: {self.scenarios_file}")
        
        scenario = MacroalgaeProtectionScenario(**scen_dict[scenario_name])

        self.scenario = scenario

        super()._load_pds_scenario()
        
        if self.scenario.ref_scenario_name:
            self._load_ref_scenario()
        else:
            # creates a ref scenario with zeroes.
            self.ref_scenario = self.pds_scenario.get_skeleton()

        self.pds_scenario.use_tam_for_co2_calcs = True
        self.ref_scenario.use_tam_for_co2_calcs = True

        # Set scenario-specific data:
        self.sequestration_rate_all_ocean = self.scenario.sequestration_rate_all_ocean
        self.npv_discount_rate = self.scenario.npv_discount_rate
        self.growth_rate_of_ocean_degradation = self.scenario.growth_rate_of_ocean_degradation
        self.disturbance_rate = 0.0

        # PDS and REF have a similar TAM structure:
        self.set_up_tam(self.pds_scenario)
        self.set_up_tam(self.ref_scenario)
        
        return

    
    def get_reduced_area_degradation(self):
        
        # reduction degraded area = (total at risk area pds) - (total at risk area ref)
        
        tara_pds = self.pds_scenario.get_total_undegraded_area(self.growth_rate_of_ocean_degradation, self.disturbance_rate, self.delay_impact_of_protection_by_one_year)
        tara_ref = self.ref_scenario.get_total_undegraded_area(self.growth_rate_of_ocean_degradation, self.disturbance_rate, self.delay_impact_of_protection_by_one_year)

        tara = tara_pds - tara_ref
        start = tara.loc[self.start_year-1]
        end = tara.loc[self.end_year]

        reduction = end - start

        return reduction


    def get_total_co2_seq(self) -> np.float64:

        # SUM('CO2 Calcs'!BL121:BL166)

        # reduction degraded area = (total at risk area pds) - (total at risk area ref)
        
        # tara_pds should equal ['Unit Adoption Calculations']!$DS$135
        tara_pds = self.pds_scenario.get_total_undegraded_area(
                                    self.growth_rate_of_ocean_degradation,
                                    self.disturbance_rate,
                                    self.delay_impact_of_protection_by_one_year)

        # tara_ref should equal ['Unit Adoption Calculations']!$DS$197
        tara_ref = self.ref_scenario.get_total_undegraded_area(
                                    self.growth_rate_of_ocean_degradation,
                                    self.disturbance_rate,
                                    self.delay_impact_of_protection_by_one_year)

        # cumulative_reduction_in_total_degraded_land should equal ['Unit Adoption Calculations']!$DS$251
        cumulative_reduction_in_total_degraded_land = tara_pds - tara_ref
        
        co2_sequestered = cumulative_reduction_in_total_degraded_land * 3.666 * self.sequestration_rate_all_ocean

        start = self.start_year
        end = self.end_year

        if self.delay_regrowth_of_degraded_land_by_one_year:
            start -= 1
            end -= 1

        result = co2_sequestered.loc[start: end].sum()
        return result / 1000


    def get_change_in_ppm_equiv(self) -> np.float64:
        
        pds_sequestration = self.pds_scenario.get_change_in_ppm_equivalent_series(
                self.sequestration_rate_all_ocean, 
                self.disturbance_rate, 
                self.growth_rate_of_ocean_degradation, 
                self.delay_impact_of_protection_by_one_year,
                self.emissions_reduced_per_unit_area,
                self.delay_regrowth_of_degraded_land_by_one_year,
                self.use_adoption_for_carbon_sequestration_calculation,
                self.direct_emissions_are_annual)

        ref_sequestration = self.ref_scenario.get_change_in_ppm_equivalent_series(
                self.sequestration_rate_all_ocean, 
                self.disturbance_rate, 
                self.growth_rate_of_ocean_degradation, 
                self.delay_impact_of_protection_by_one_year,
                self.emissions_reduced_per_unit_area,
                self.delay_regrowth_of_degraded_land_by_one_year,
                self.use_adoption_for_carbon_sequestration_calculation,
                self.direct_emissions_are_annual)

        net_sequestration = (pds_sequestration - ref_sequestration)
        # net_sequestration should now equal 'CO2-eq PPM Calculator' on tab [CO2 Calcs]!$B$224

        end = self.end_year
        if self.delay_regrowth_of_degraded_land_by_one_year:
            end -= 1
        result = net_sequestration.loc[end]

        return result


    def get_change_in_ppm_equivalent_final_year(self) -> np.float64:
                
        pds_sequestration = self.pds_scenario.get_change_in_ppm_equivalent_series(
                self.sequestration_rate_all_ocean, 
                self.disturbance_rate, 
                self.growth_rate_of_ocean_degradation, 
                self.delay_impact_of_protection_by_one_year,
                self.emissions_reduced_per_unit_area,
                self.delay_regrowth_of_degraded_land_by_one_year,
                self.use_adoption_for_carbon_sequestration_calculation,
                self.direct_emissions_are_annual)

        ref_sequestration = self.ref_scenario.get_change_in_ppm_equivalent_series(
                self.sequestration_rate_all_ocean, 
                self.disturbance_rate, 
                self.growth_rate_of_ocean_degradation, 
                self.delay_impact_of_protection_by_one_year,
                self.emissions_reduced_per_unit_area,
                self.delay_regrowth_of_degraded_land_by_one_year,
                self.use_adoption_for_carbon_sequestration_calculation,
                self.direct_emissions_are_annual)

        # net_sequestration should equal 'CO2-eq PPM Calculator' on tab [CO2 Calcs]!$B$224
        net_sequestration = (pds_sequestration - ref_sequestration)

        end = self.end_year
        if self.delay_regrowth_of_degraded_land_by_one_year:
            end -= 1
        
        result = net_sequestration.loc[end] - net_sequestration.loc[end-1]

        return result
