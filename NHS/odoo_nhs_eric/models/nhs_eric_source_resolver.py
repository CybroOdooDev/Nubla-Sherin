# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, models

class NhsEricSourceResolver(models.Model):
    _name = 'nhs.eric.source.resolver'
    _description = 'ERIC Source Resolver (service model)'
    _transient = True

    @api.model
    def resolve(self, source_key, company, year=None, site=None):
        """
        Resolve a source key to a value from the estate/compliance modules.

        Args:
            source_key (str): The source key to resolve, e.g. "estate.total_gia"
            company (recordset): The company/organisation to scope the data
            year (str, optional): The financial year for data scoping
            site (recordset, optional): Specific site for site-level aggregation

        Returns:
            The resolved value (float, dict, or None if not found)
        """
        if not source_key:
            return None

        self.env.flush_all()

        self = self.sudo()
        if company:
            self = self.with_company(company)
            company = company.sudo()
        if site:
            site = site.sudo()

        try:
            parts = source_key.split('.')
            if len(parts) < 2:
                return None

            module = parts[0]
            key = '.'.join(parts[1:])

            if module == 'estate':
                return self._resolve_estate(key, company, year, site=site)
            elif module == 'compliance':
                return self._resolve_compliance(key, company, year, site=site)
            elif module == 'energy':
                # Placeholder for future energy module
                return None
            else:
                return None
        except Exception:
            return None

    def _resolve_estate(self, key, company, year, site=None):
        """Resolve estate-related keys from the Estate Register."""
        if key == 'total_gia':
            return self._get_total_gia(company, site=site)
        elif key == 'site_count':
            return self._get_site_count(company, site=site)
        elif key == 'building_count':
            return self._get_building_count(company, site=site)
        elif key == 'land_area':
            return self._get_land_area(company, site=site)
        elif key == 'occupied_floor_area':
            return self._get_occupied_floor_area(company, site=site)
        elif key == 'backlog.high':
            return self._get_backlog_by_risk(company, 'high', site=site)
        elif key == 'backlog.significant':
            return self._get_backlog_by_risk(company, 'significant', site=site)
        elif key == 'backlog.moderate':
            return self._get_backlog_by_risk(company, 'moderate', site=site)
        elif key == 'backlog.low':
            return self._get_backlog_by_risk(company, 'low', site=site)
        elif key == 'backlog.total':
            return self._get_total_backlog(company, site=site)
        elif key == 'age_bands':
            return self._get_age_bands(company, site=site)
        elif key.startswith('age_bands.'):
            band = key.split('.')[1]
            return float(self._get_age_bands(company, site=site).get(band, 0))
        elif key.startswith('age_bands_pct.'):
            band = key.split('.')[1]
            return self._get_age_bands_pct(company, band, site=site)
        elif key == 'tenure.owned':
            return self._get_tenure_percentage(company, 'owned', site=site)
        elif key == 'tenure.leased':
            return self._get_tenure_percentage(company, 'leased', site=site)
        elif key == 'condition':
            return self._get_condition(company, site=site)
        elif key.startswith('condition.count.'):
            grade = key.split('.')[2]
            return float(self._get_condition_count(company, grade, site=site))
        elif key.startswith('condition.'):
            grade = key.split('.')[1]
            return self._get_condition_percentage(company, grade, site=site)
        else:
            return None

    def _resolve_compliance(self, key, company, year, site=None):
        """Resolve compliance-related keys from Estates Compliance."""
        if key == 'pct':
            return self._get_overall_compliance(company, site=site)
        elif key == 'overdue_count':
            return self._get_overdue_count(company, site=site)
        else:
            return self._get_compliance_percentage(company, key, site=site)

    def _get_total_gia(self, company, site=None):
        """
        Get total GIA from Estate Register.
        Source: Estate Register - Total Gross Internal Area
        """
        if site:
            return site.total_gia or 0.0
        Site = self.env['nhs.estate.site']
        sites = Site.search([('company_id', '=', company.id), ('active', '=', True)])
        return sum(sites.mapped('total_gia') or [])

    def _get_site_count(self, company, site=None):
        """
        Get number of sites from Estate Register.
        Source: Estate Register - Site Count
        """
        if site:
            return 1
        Site = self.env['nhs.estate.site']
        return Site.search_count([('company_id', '=', company.id), ('active', '=', True)])

    def _get_building_count(self, company, site=None):
        """
        Get number of buildings from Estate Register.
        Source: Estate Register - Building Count
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        return Building.search_count(domain)

    def _get_land_area(self, company, site=None):
        """
        Get total land area from Estate Register.
        Source: Estate Register - Land Area
        """
        if site:
            return site.land_area_ha or 0.0
        Site = self.env['nhs.estate.site']
        sites = Site.search([('company_id', '=', company.id), ('active', '=', True)])
        return sum(sites.mapped('land_area_ha') or [])

    def _get_occupied_floor_area(self, company, site=None):
        """
        Get occupied floor area from Estate Register.
        Source: Estate Register - Occupied Floor Area
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        buildings = Building.search(domain)
        return sum(buildings.mapped('occupied_area') or [])

    def _get_backlog_by_risk(self, company, risk_level, site=None):
        """
        Get backlog cost by risk category from Estate Register.
        Source: Estate Register - Backlog Maintenance Cost by Risk Category
        Risk levels: high, significant, moderate, low
        """
        Backlog = self.env['nhs.estate.backlog']
        domain = [('risk_category', '=', risk_level), ('active', '=', True), ('status', '!=', 'resolved'), ('building_id.active', '=', True)]
        if site:
            domain.append(('building_id.site_id', '=', site.id))
        else:
            domain.append(('building_id.company_id', '=', company.id))
        backlog_items = Backlog.search(domain)
        return sum(backlog_items.mapped('cost_estimate') or [])

    def _get_total_backlog(self, company, site=None):
        """
        Get total backlog cost from Estate Register.
        Source: Estate Register - Total Backlog Maintenance Cost
        """
        Backlog = self.env['nhs.estate.backlog']
        domain = [('active', '=', True), ('status', '!=', 'resolved'), ('building_id.active', '=', True)]
        if site:
            domain.append(('building_id.site_id', '=', site.id))
        else:
            domain.append(('building_id.company_id', '=', company.id))
        backlog_items = Backlog.search(domain)
        return sum(backlog_items.mapped('cost_estimate') or [])

    def _get_age_bands(self, company, site=None):
        """
        Get building age distribution from Estate Register.
        Source: Estate Register - Building Age Profile from build years
        Age bands: pre_1980, 1980_2000, post_2000
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        buildings = Building.search(domain)

        age_bands = {
            'pre_1980': 0,
            '1980_2000': 0,
            'post_2000': 0
        }

        for building in buildings:
            if not building.build_year:
                continue
            if building.build_year < 1980:
                age_bands['pre_1980'] += 1
            elif building.build_year < 2000:
                age_bands['1980_2000'] += 1
            else:
                age_bands['post_2000'] += 1

        return age_bands

    def _get_age_bands_pct(self, company, band, site=None):
        """
        Get percentage of total building GIA in a specific age band.
        Source: Estate Register - Building Age Profile (%)
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        buildings = Building.search(domain)
        
        buildings_with_year = buildings.filtered(lambda b: b.build_year > 0)
        total_gia = sum(buildings_with_year.mapped('gia') or [])
        if not total_gia:
            return 0.0

        band_buildings = self.env['nhs.estate.building']
        for building in buildings_with_year:
            if building.build_year < 1980:
                b_band = 'pre_1980'
            elif building.build_year < 2000:
                b_band = '1980_2000'
            else:
                b_band = 'post_2000'
            if b_band == band:
                band_buildings |= building

        band_gia = sum(band_buildings.mapped('gia') or [])
        return (band_gia / total_gia) * 100.0

    def _get_tenure_percentage(self, company, tenure_type, site=None):
        """
        Get tenure percentage from Estate Register based on building GIA.
        Source: Estate Register - Tenure/Ownership Split
        Tenure types: owned (freehold), leased (leasehold, licence, PFI, LIFT, NHSPS, CHP)
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))

        buildings = Building.search(domain)
        buildings_with_tenure = buildings.filtered(lambda b: b.tenure_type)
        total_area = sum(buildings_with_tenure.mapped('gia') or [])
        if not total_area:
            return 0.0

        if tenure_type == 'owned':
            allowed_types = ['freehold']
        else:  # leased
            allowed_types = ['leasehold', 'licence', 'pfi', 'lift', 'nhsps', 'chp']

        tenure_buildings = buildings_with_tenure.filtered(lambda b: b.tenure_type in allowed_types)
        tenure_area = sum(tenure_buildings.mapped('gia') or [])

        return (tenure_area / total_area) * 100.0

    def _get_condition(self, company, site=None):
        """
        Get average condition rating from Estate Register.
        Source: Estate Register - Estate Condition (Six Facet-derived)
        Grades: A=4.0, B=3.0, C=2.0, D=1.0
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        buildings = Building.search(domain)

        if not buildings:
            return 0.0

        grade_map = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0}
        grades = [grade_map.get(b.latest_condition_grade, 0.0) for b in buildings if
                  b.latest_condition_grade in grade_map]
        if not grades:
            return 0.0

        return sum(grades) / len(grades)

    def _get_condition_percentage(self, company, grade, site=None):
        """
        Get the percentage of total building GIA in a specific condition grade.
        Source: Estate Register - Estate Condition by Grade
        Grades: A, B, C, D
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        buildings = Building.search(domain)
        
        buildings_with_grade = buildings.filtered(lambda b: b.latest_condition_grade)
        total_gia = sum(buildings_with_grade.mapped('gia') or [])
        if not total_gia:
            return 0.0

        grade_buildings = buildings_with_grade.filtered(lambda b: b.latest_condition_grade == grade)
        grade_gia = sum(grade_buildings.mapped('gia') or [])
        return (grade_gia / total_gia) * 100.0

    def _get_condition_count(self, company, grade, site=None):
        """
        Get the count of buildings in a specific condition grade.
        Source: Estate Register - Estate Condition Count by Grade
        """
        Building = self.env['nhs.estate.building']
        domain = [('company_id', '=', company.id), ('active', '=', True)]
        if site:
            domain.append(('site_id', '=', site.id))
        if grade:
            domain.append(('latest_condition_grade', '=', grade))
        return Building.search_count(domain)

    def _get_compliance_items(self, company, site=None, discipline=None):
        """
        Helper to fetch active, applicable compliance items filtered by company, site, and discipline.
        Source: Estates Compliance - Statutory-compliance status by discipline
        """
        domain = [('active', '=', True), ('company_id', '=', company.id)]
        if site:
            domain.append('|')
            domain.append(('site_id', '=', site.id))
            domain.append('|')
            domain.append(('building_id.site_id', '=', site.id))
            domain.append(('space_id.building_id.site_id', '=', site.id))

        if discipline:
            mapping = {
                'fire': 'FIRE',
                'water': 'WATER',
                'electrical': 'ELEC',
                'asbestos': 'ASB',
                'vent': 'VENT',
                'loler': 'LOLER',
                'mgps': 'MGPS',
                'pressure': 'PSSR',
                'gas': 'GAS',
                'lightning': 'LIGHT',
                'drainage': 'DRAIN',
                'working_at_height': 'WAH',
            }
            mapped_code = mapping.get(discipline, discipline.upper())
            dis_domain = ['|', ('code', '=', mapped_code), ('name', '=ilike', discipline.replace('_', ' '))]

            discipline_rec = self.env['nhs.compliance.discipline'].search(dis_domain, limit=1)
            if not discipline_rec:
                return self.env['nhs.compliance.item']
            domain.append(('discipline_id', '=', discipline_rec.id))

        return self.env['nhs.compliance.item'].search(domain)

    def _get_compliance_percentage(self, company, discipline, site=None):
        """
        Get compliance percentage for a specific discipline.
        Source: Estates Compliance - Statutory-compliance status by discipline
        Disciplines: fire, water, electrical, asbestos, etc.
        """
        items = self._get_compliance_items(company, site=site, discipline=discipline)
        applicable_items = items.filtered(lambda i: i.status != 'not_applicable')
        if not applicable_items:
            return 0.0
        compliant_items = applicable_items.filtered(lambda i: i.status in ('compliant', 'due_soon'))
        return (len(compliant_items) / len(applicable_items)) * 100.0

    def _get_overall_compliance(self, company, site=None):
        """
        Get overall compliance percentage across all disciplines.
        Source: Estates Compliance - Overall Statutory-compliance status
        """
        items = self._get_compliance_items(company, site=site)
        applicable_items = items.filtered(lambda i: i.status != 'not_applicable')
        if not applicable_items:
            return 0.0
        compliant_items = applicable_items.filtered(lambda i: i.status in ('compliant', 'due_soon'))
        return (len(compliant_items) / len(applicable_items)) * 100.0

    def _get_overdue_count(self, company, site=None):
        """
        Get count of overdue compliance items.
        Source: Estates Compliance - Overdue compliance items
        """
        items = self._get_compliance_items(company, site=site)
        overdue_items = items.filtered(lambda i: i.status in ('overdue'))
        return len(overdue_items)

    @api.model
    def get_traceability_note(self, source_key, company, year=None, site=None):
        """
        Generate a detailed record-by-record traceability note for a resolved key.
        Provides clear indication of which source and record each value came from.
        """
        if not source_key:
            return "Manual entry"

        self.env.flush_all()

        self = self.sudo()
        if company:
            self = self.with_company(company)
            company = company.sudo()
        if site:
            site = site.sudo()

        try:
            parts = source_key.split('.')
            if len(parts) < 2:
                return f"Auto from {source_key}"

            module = parts[0]
            key = '.'.join(parts[1:])

            if module == 'estate':
                return self._get_estate_traceability(key, company, year, site)
            elif module == 'compliance':
                return self._get_compliance_traceability(key, company, year, site)
            else:
                return f"Auto from {source_key}"
        except Exception as e:
            return f"Auto from {source_key} (Error generating details: {str(e)})"

    def _get_estate_traceability(self, key, company, year, site=None):
        """
        Generate traceability note for estate-related keys.
        Shows which records contributed to the value.
        """
        notes = []
        source_name = "Estate Register"

        # Site count, building count and GIA
        if key == 'total_gia':
            if site:
                notes.append(f"Site: {site.name} ({site.code or 'No Code'}) - GIA: {site.total_gia or 0.0} m²")
            else:
                sites = self.env['nhs.estate.site'].search([('company_id', '=', company.id), ('active', '=', True)])
                for s in sites:
                    notes.append(f"Site: {s.name} ({s.code or 'No Code'}) - GIA: {s.total_gia or 0.0} m²")
            return f"{source_name} — Total GIA. Details:\n" + "\n".join(notes)

        elif key == 'site_count':
            if site:
                notes.append(f"Site: {site.name} ({site.code or 'No Code'})")
            else:
                sites = self.env['nhs.estate.site'].search([('company_id', '=', company.id), ('active', '=', True)])
                for s in sites:
                    notes.append(f"Site: {s.name} ({s.code or 'No Code'})")
            return f"{source_name} — Site Count. Details:\n" + "\n".join(notes)

        elif key == 'building_count':
            domain = [('company_id', '=', company.id), ('active', '=', True)]
            if site:
                domain.append(('site_id', '=', site.id))
            buildings = self.env['nhs.estate.building'].search(domain)
            for b in buildings:
                notes.append(f"Building: {b.name} ({b.code or 'No Code'}) [Site: {b.site_id.name}]")
            return f"{source_name} — Building Count. Details:\n" + "\n".join(notes)

        # Land area and occupied floor area
        elif key == 'land_area':
            if site:
                notes.append(f"Site: {site.name} ({site.code or 'No Code'}) - Land Area: {site.land_area_ha or 0.0} ha")
            else:
                sites = self.env['nhs.estate.site'].search([('company_id', '=', company.id), ('active', '=', True)])
                for s in sites:
                    notes.append(f"Site: {s.name} ({s.code or 'No Code'}) - Land Area: {s.land_area_ha or 0.0} ha")
            return f"{source_name} — Land Area. Details:\n" + "\n".join(notes)

        elif key == 'occupied_floor_area':
            domain = [('company_id', '=', company.id), ('active', '=', True)]
            if site:
                domain.append(('site_id', '=', site.id))
            buildings = self.env['nhs.estate.building'].search(domain)
            for b in buildings:
                notes.append(f"Building: {b.name} ({b.code or 'No Code'}) - Occupied Area: {b.occupied_area or 0.0} m²")
            return f"{source_name} — Occupied Floor Area. Details:\n" + "\n".join(notes)

        # Backlog maintenance cost by risk category
        elif key.startswith('backlog.'):
            risk_level = key.split('.')[1]
            Backlog = self.env['nhs.estate.backlog']
            domain = [('active', '=', True), ('status', '!=', 'resolved'), ('building_id.active', '=', True)]
            if risk_level != 'total':
                domain.append(('risk_category', '=', risk_level))
            if site:
                domain.append(('building_id.site_id', '=', site.id))
            else:
                domain.append(('building_id.company_id', '=', company.id))
            backlog_items = Backlog.search(domain)
            for item in backlog_items:
                notes.append(
                    f"Backlog Item: {item.name or 'Unnamed'} [Building: {item.building_id.name}] - Cost: £{item.cost_estimate or 0.0} (Risk: {item.risk_category})")
            return f"{source_name} — Backlog Cost ({risk_level}). Details:\n" + (
                "\n".join(notes) if notes else "No backlog records found.")

        # Building age profile from build years
        elif key.startswith('age_bands'):
            band = key.split('.')[1] if '.' in key else None
            domain = [('company_id', '=', company.id), ('active', '=', True)]
            if site:
                domain.append(('site_id', '=', site.id))
            buildings = self.env['nhs.estate.building'].search(domain)
            for b in buildings:
                if not b.build_year:
                    continue
                if b.build_year < 1980:
                    b_band = 'pre_1980'
                elif b.build_year < 2000:
                    b_band = '1980_2000'
                else:
                    b_band = 'post_2000'

                if not band or b_band == band:
                    notes.append(
                        f"Building: {b.name} ({b.code or 'No Code'}) - Built: {b.build_year or 'Unknown'} (GIA: {b.gia or 0.0} m²)")
            return f"{source_name} — Building Age Profile ({band or 'all'}). Details:\n" + (
                "\n".join(notes) if notes else "No matching buildings found.")

        # Tenure/ownership split
        elif key.startswith('tenure.'):
            tenure_type = key.split('.')[1]
            domain = [('company_id', '=', company.id), ('active', '=', True)]
            if site:
                domain.append(('site_id', '=', site.id))
            buildings = self.env['nhs.estate.building'].search(domain)
            if tenure_type == 'owned':
                allowed_types = ['freehold']
                label = "Owned"
            else:
                allowed_types = ['leasehold', 'licence', 'pfi', 'lift', 'nhsps', 'chp']
                label = "Leased"
            for b in buildings:
                if b.tenure_type in allowed_types:
                    notes.append(
                        f"Building: {b.name} ({b.code or 'No Code'}) - Tenure: {b.tenure_type or 'Unknown'} (GIA: {b.gia or 0.0} m²)")
            return f"{source_name} — Tenure Split ({label}). Details:\n" + (
                "\n".join(notes) if notes else "No matching buildings found.")

        # Estate condition (Six Facet-derived)
        elif key.startswith('condition'):
            grade = None
            if key == 'condition':
                label = "Average"
            elif key.startswith('condition.count.'):
                grade = key.split('.')[2]
                label = f"Count of Grade {grade}"
            elif key.startswith('condition.'):
                grade = key.split('.')[1]
                label = f"Percentage of Grade {grade}"
            else:
                label = "Condition"

            domain = [('company_id', '=', company.id), ('active', '=', True)]
            if site:
                domain.append(('site_id', '=', site.id))
            buildings = self.env['nhs.estate.building'].search(domain)
            for b in buildings:
                if not grade or b.latest_condition_grade == grade:
                    notes.append(
                        f"Building: {b.name} ({b.code or 'No Code'}) - Condition: {b.latest_condition_grade or 'None'} (GIA: {b.gia or 0.0} m²)")
            return f"{source_name} — Condition Rating ({label}). Details:\n" + (
                "\n".join(notes) if notes else "No matching buildings found.")

        return f"{source_name} — {key}"

    def _get_compliance_traceability(self, key, company, year, site=None):
        """
        Generate traceability note for compliance-related keys.
        Source: Estates Compliance - Statutory-compliance status by discipline
        """
        notes = []
        source_name = "Estates Compliance"

        if key == 'pct':
            items = self._get_compliance_items(company, site=site)
            for item in items:
                notes.append(f"Item: {item.name} [Discipline: {item.discipline_id.name}] - Status: {item.status}")
            return f"{source_name} — Overall Compliance %. Details:\n" + (
                "\n".join(notes) if notes else "No compliance items found.")

        elif key == 'overdue_count':
            items = self._get_compliance_items(company, site=site)
            overdue = items.filtered(lambda i: i.status in ('overdue', 'failed'))
            for item in overdue:
                notes.append(
                    f"Overdue Item: {item.name} [Discipline: {item.discipline_id.name}] - Status: {item.status}")
            return f"{source_name} — Overdue Count. Details:\n" + (
                "\n".join(notes) if notes else "No overdue items found.")

        else:
            # key is a discipline
            items = self._get_compliance_items(company, site=site, discipline=key)
            for item in items:
                notes.append(f"Item: {item.name} - Status: {item.status} (Next Test: {item.next_due_date or 'None'})")
            return f"{source_name} — Discipline ({key}) %. Details:\n" + (
                "\n".join(notes) if notes else "No matching compliance items found.")

    @api.model
    def available_keys(self):
        """List all available source keys for configuration."""
        return [
            # Site count, building count and GIA
            'estate.total_gia',
            'estate.site_count',
            'estate.building_count',
            # Land area and occupied floor area
            'estate.land_area',
            'estate.occupied_floor_area',
            # Backlog maintenance cost by risk category
            'estate.backlog.high',
            'estate.backlog.significant',
            'estate.backlog.moderate',
            'estate.backlog.low',
            'estate.backlog.total',
            # Building age profile
            'estate.age_bands.pre_1980',
            'estate.age_bands.1980_2000',
            'estate.age_bands.post_2000',
            'estate.age_bands_pct.pre_1980',
            'estate.age_bands_pct.1980_2000',
            'estate.age_bands_pct.post_2000',
            # Tenure/ownership split
            'estate.tenure.owned',
            'estate.tenure.leased',
            # Estate condition (Six Facet-derived)
            'estate.condition',
            'estate.condition.A',
            'estate.condition.B',
            'estate.condition.C',
            'estate.condition.D',
            'estate.condition.count.A',
            'estate.condition.count.B',
            'estate.condition.count.C',
            'estate.condition.count.D',
            # Statutory-compliance status by discipline
            'compliance.fire',
            'compliance.water',
            'compliance.electrical',
            'compliance.asbestos',
            'compliance.vent',
            'compliance.loler',
            'compliance.mgps',
            'compliance.pressure',
            'compliance.gas',
            'compliance.lightning',
            'compliance.drainage',
            'compliance.working_at_height',
            'compliance.pct',
            'compliance.overdue_count',
            # Placeholders for future modules
            'energy.electricity',
            'energy.gas',
            'energy.carbon',
            'energy.water',
        ]

    @api.model
    def get_key_description(self, source_key):
        """Get a human-readable description for a source key."""
        descriptions = {
            'estate.total_gia': 'Total Gross Internal Area (m²) - Estate Register',
            'estate.site_count': 'Number of Sites - Estate Register',
            'estate.building_count': 'Number of Buildings - Estate Register',
            'estate.land_area': 'Land Area (hectares) - Estate Register',
            'estate.occupied_floor_area': 'Occupied Floor Area (m²) - Estate Register',
            'estate.backlog.high': 'Backlog - High Risk (£) - Estate Register',
            'estate.backlog.significant': 'Backlog - Significant Risk (£) - Estate Register',
            'estate.backlog.moderate': 'Backlog - Moderate Risk (£) - Estate Register',
            'estate.backlog.low': 'Backlog - Low Risk (£) - Estate Register',
            'estate.backlog.total': 'Backlog - Total (£) - Estate Register',
            'estate.age_bands.pre_1980': 'Buildings Built Before 1980 (count) - Estate Register',
            'estate.age_bands.1980_2000': 'Buildings Built 1980-2000 (count) - Estate Register',
            'estate.age_bands.post_2000': 'Buildings Built After 2000 (count) - Estate Register',
            'estate.age_bands_pct.pre_1980': 'GIA % - Buildings Built Before 1980 - Estate Register',
            'estate.age_bands_pct.1980_2000': 'GIA % - Buildings Built 1980-2000 - Estate Register',
            'estate.age_bands_pct.post_2000': 'GIA % - Buildings Built After 2000 - Estate Register',
            'estate.tenure.owned': 'Owned Tenure (% of GIA) - Estate Register',
            'estate.tenure.leased': 'Leased Tenure (% of GIA) - Estate Register',
            'estate.condition': 'Average Condition Rating - Estate Register',
            'estate.condition.A': 'Condition Grade A (% of GIA) - Estate Register',
            'estate.condition.B': 'Condition Grade B (% of GIA) - Estate Register',
            'estate.condition.C': 'Condition Grade C (% of GIA) - Estate Register',
            'estate.condition.D': 'Condition Grade D (% of GIA) - Estate Register',
            'estate.condition.count.A': 'Condition Grade A (count) - Estate Register',
            'estate.condition.count.B': 'Condition Grade B (count) - Estate Register',
            'estate.condition.count.C': 'Condition Grade C (count) - Estate Register',
            'estate.condition.count.D': 'Condition Grade D (count) - Estate Register',
            'compliance.fire': 'Fire Safety Compliance (%) - Estates Compliance',
            'compliance.water': 'Water Safety Compliance (%) - Estates Compliance',
            'compliance.electrical': 'Electrical Safety Compliance (%) - Estates Compliance',
            'compliance.asbestos': 'Asbestos Management Compliance (%) - Estates Compliance',
            'compliance.vent' : 'Ventilation Safety (%) - Estates Compliance',
            'compliance.loler' : 'Lifting (LOLER) (%) - Estates Compliance',
            'compliance.mgps' : 'Medical Gas (MGPS) (%) - Estates Compliance',
            'compliance.pressure' : 'Pressure Systems (%) - Estates Compliance',
            'compliance.gas' : 'Gas Safety (%) - Estates Compliance',
            'compliance.lightning' : 'Lightning Protection (%) - Estates Compliance',
            'compliance.drainage' : 'Drainage Systems (%) - Estates Compliance',
            'compliance.working_at_height' : 'Working at Height (%) - Estates Compliance',
            'compliance.pct': 'Overall Compliance (%) - Estates Compliance ',
            'compliance.overdue_count': 'Number of Overdue Compliance Items - Estates Compliance',
        }
        return descriptions.get(source_key, source_key)