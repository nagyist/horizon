# Copyright 2012 NEC Corporation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging

from django.template import defaultfilters as filters
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from horizon import exceptions
from horizon import tables

from openstack_dashboard import api
from openstack_dashboard.dashboards.admin.networks \
    import utils as admin_utils
from openstack_dashboard.dashboards.project.networks \
    import tables as project_tables
from openstack_dashboard import policy
from openstack_dashboard.utils import settings as setting_utils


LOG = logging.getLogger(__name__)


class CreateNetwork(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Network")
    url = "horizon:admin:networks:create"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("network", "create_network"),)


class EditNetwork(policy.PolicyTargetMixin, tables.LinkAction):
    name = "update"
    verbose_name = _("Edit Network")
    url = "horizon:admin:networks:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("network", "update_network"),)


class CreateSubnet(project_tables.CreateSubnet):
    url = "horizon:admin:networks:createsubnet"

    def allowed(self, request, datum=None):
        return True


DISPLAY_CHOICES = (
    ("up", pgettext_lazy("Admin state of a Network", "UP")),
    ("down", pgettext_lazy("Admin state of a Network", "DOWN")),
)


def get_availability_zones(network):
    if 'availability_zones' in network and network.availability_zones:
        return ', '.join(network.availability_zones)
    return _("-")


class AdminNetworksFilterAction(project_tables.ProjectNetworksFilterAction):
    name = "filter_admin_networks"
    filter_choices = (('project', _("Project ="), True),) +\
        project_tables.ProjectNetworksFilterAction.filter_choices


class NetworksTable(tables.DataTable):
    tenant = tables.Column("tenant_name", verbose_name=_("Project"))
    name = tables.WrappingColumn("name_or_id", verbose_name=_("Network Name"),
                                 link='horizon:admin:networks:detail')
    subnets = tables.Column(project_tables.get_subnets,
                            verbose_name=_("Subnets Associated"),)
    num_agents = tables.Column("num_agents",
                               verbose_name=_("DHCP Agents"))
    shared = tables.Column("is_shared", verbose_name=_("Shared"),
                           filters=(filters.yesno, filters.capfirst))
    external = tables.Column("is_router_external",
                             verbose_name=_("External"),
                             filters=(filters.yesno, filters.capfirst))
    status = tables.Column(
        "status", verbose_name=_("Status"),
        display_choices=project_tables.STATUS_DISPLAY_CHOICES)
    admin_state = tables.Column("admin_state",
                                verbose_name=_("Admin State"),
                                display_choices=DISPLAY_CHOICES)
    availability_zones = tables.Column(get_availability_zones,
                                       verbose_name=_("Availability Zones"))

    def get_object_display(self, network):
        return network.name_or_id

    class Meta(object):
        name = "networks"
        verbose_name = _("Networks")
        table_actions = (CreateNetwork, project_tables.DeleteNetwork,
                         AdminNetworksFilterAction)
        row_actions = (EditNetwork, CreateSubnet, project_tables.DeleteNetwork)

    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
        super().__init__(request, data=data,
                         needs_form_wrapper=needs_form_wrapper,
                         **kwargs)
        try:
            if not api.neutron.is_extension_supported(
                    request, "network_availability_zone"):
                del self.columns["availability_zones"]
        except Exception:
            msg = _("Unable to check if network availability zone extension "
                    "is supported")
            exceptions.handle(self.request, msg)
            del self.columns['availability_zones']

        show_agents_column = setting_utils.get_dict_config(
            'OPENSTACK_NEUTRON_NETWORK', 'show_agents_column')
        if not (show_agents_column and
                admin_utils.is_dhcp_agent_scheduler_supported(request)):
            del self.columns['num_agents']
