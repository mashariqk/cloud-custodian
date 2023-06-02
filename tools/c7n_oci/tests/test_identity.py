# Copyright The Cloud Custodian Authors.
# SPDX-License-id: Apache-2.0

import inspect
import unittest

import pytest
from c7n_oci.constants import COMPARTMENT_IDS
from oci_common import Module, OciBaseTest, Resource, Scope
from pytest_terraform import terraform

from c7n.testing import C7N_FUNCTIONAL


class TestIdentityTerraformTest(OciBaseTest):
    def _get_identity_compartment_details(self, identity_compartment):
        compartment_id = identity_compartment[
            "oci_identity_compartment.test_compartment.compartment_id"
        ]
        new_compartment_id = identity_compartment["oci_identity_compartment.test_compartment.id"]
        return compartment_id, new_compartment_id

    @terraform(Module.IDENTITY_COMPARTMENT.value, scope=Scope.CLASS.value)
    def test_identity_compartment(self, identity_compartment, test):
        compartment_id, new_compartment_id = self._get_identity_compartment_details(
            identity_compartment
        )
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy_str = {
            "name": "filter-and-add-tags-on-compartments",
            "description": "Filter and add tags on the compartment",
            "resource": Resource.COMPARTMENT.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "value",
                    "key": "freeform_tags.Cloud_Custodian_Test",
                    "value": "True",
                    "op": "eq",
                },
            ],
            "actions": [
                {
                    "type": "update-compartment",
                    "params": {
                        "update_compartment_details": {
                            "freeform_tags": {"Environment": "Development"}
                        }
                    },
                }
            ],
        }
        policy = test.load_policy(policy_str, session_factory=session_factory)
        policy.run()
        resource = self.fetch_validation_data(
            policy.resource_manager, "get_compartment", new_compartment_id
        )
        assert resource is not None
        test.assertEqual(resource["freeform_tags"]["Environment"], "Development")

    @terraform(Module.IDENTITY_GROUP.value, scope=Scope.CLASS.value)
    def test_identity_group(self, identity_group, test):
        compartment_id = identity_group["oci_identity_group.test_group.compartment_id"]
        group_id = identity_group["oci_identity_group.test_group.id"]
        policy_str = {
            "name": "filter-and-add-tags-on-group",
            "description": "Filter and add tags on the group",
            "resource": Resource.GROUP.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "value",
                    "key": "freeform_tags.Cloud_Custodian",
                    "value": "Present",
                    "op": "eq",
                },
            ],
            "actions": [
                {
                    "type": "update-group",
                    "params": {
                        "update_group_details": {"freeform_tags": {"Environment": "Development"}}
                    },
                }
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        policy.run()
        resource = self.fetch_validation_data(policy.resource_manager, "get_group", group_id)
        assert resource is not None
        test.assertEqual(resource["name"], "Custodian-Dev-Group")
        test.assertEqual(resource["freeform_tags"]["Environment"], "Development")

    def _get_user_details(self, identity_user):
        compartment_id = identity_user["oci_identity_user.test_user.compartment_id"]
        user_ocid = identity_user["oci_identity_user.test_user.id"]
        return compartment_id, user_ocid

    @terraform(Module.IDENTITY_USER.value, scope=Scope.CLASS.value)
    def test_identity_user_tag(self, identity_user, test):
        compartment_id, user_ocid = self._get_user_details(identity_user)
        policy_str = {
            "name": "filter-and-add-tags-on-user",
            "description": "Filter and add tags on the user",
            "resource": Resource.USER.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {"type": "value", "key": "id", "value": user_ocid},
                {
                    "type": "value",
                    "key": "freeform_tags.Cloud_Custodian",
                    "value": "True",
                    "op": "eq",
                },
            ],
            "actions": [
                {
                    "type": "update-user",
                    "params": {"update_user_details": {"freeform_tags": {"key_limit": "2"}}},
                }
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        policy.run()
        resource = self.fetch_validation_data(policy.resource_manager, "get_user", user_ocid)
        assert resource is not None
        test.assertEqual(resource["freeform_tags"]["key_limit"], "2")

    @terraform(Module.IDENTITY_USER.value, scope=Scope.CLASS.value)
    def test_identity_user_cross_filter_size(self, identity_user, test):
        """
        Cross filter size policy testcase
        """
        compartment_id, user_ocid = self._get_user_details(identity_user)
        policy_str = {
            "name": "filter_auth_tokens_based_on_size",
            "description": "Filter users with auth tokens equal to 2",
            "resource": Resource.USER.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "auth-tokens",
                    "key": "auth_tokens",
                    "value": 2,
                    "op": "eq",
                    "value_type": "size",
                },
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        policy.run()
        resources = self.fetch_validation_data(
            policy.resource_manager, "list_auth_tokens", user_ocid
        )
        resources = policy.run()
        test_user_found = False
        for resource in resources:
            if resource["id"] == user_ocid:
                test_user_found = True
                break
        assert test_user_found

    @terraform(Module.IDENTITY_USER.value, scope=Scope.CLASS.value)
    def test_identity_user_cross_filter_age(self, identity_user, test):
        """
        Cross filter query filter based on the created time usecase
        """
        compartment_id, user_ocid = self._get_user_details(identity_user)
        policy_str = {
            "name": "filter_auth_tokens_based_on_age",
            "description": "Filter users with age less than 1 year",
            "resource": Resource.USER.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "auth-tokens",
                    "key": "auth_token.time_created",
                    "value": "2023/01/01",
                    "op": "greater-than",
                    "value_type": "date",
                },
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        policy.run()
        resources = policy.run()
        test_user_found = False
        for resource in resources:
            if resource["id"] == user_ocid:
                test_user_found = True
                break
        assert test_user_found

    @terraform(Module.IDENTITY_USER.value, scope=Scope.CLASS.value)
    def test_identity_user_cross_size_age(self, identity_user, test):
        """
        Cross filter query filter with size & age filter
        """
        compartment_id, user_ocid = self._get_user_details(identity_user)
        policy_str = {
            "name": "filter_auth_tokens_based_on_size_age",
            "description": "Filter users with age less than 1 year and size equal to 2",
            "resource": Resource.USER.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "auth-tokens",
                    "key": "auth_tokens",
                    "value": 2,
                    "op": "eq",
                    "value_type": "size",
                },
                {
                    "type": "auth-tokens",
                    "key": "auth_token.time_created",
                    "value": "2023/01/01",
                    "op": "greater-than",
                    "value_type": "date",
                },
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        resources = policy.run()
        test_user_found = False
        for resource in resources:
            if resource["id"] == user_ocid:
                test_user_found = True
                break
        assert test_user_found

    @pytest.mark.skipif((not C7N_FUNCTIONAL), reason="Functional test")
    @terraform(Module.IDENTITY_USER.value, scope=Scope.CLASS.value)
    def test_identity_user_cross_age_size(self, identity_user, test):
        """
        Cross filter query filter with age & size filter
        """
        compartment_id, user_ocid = self._get_user_details(identity_user)
        policy_str = {
            "name": "filter_auth_tokens_based_on_age",
            "description": "Filter users with age less than 1 yr and size equal to 2",
            "resource": Resource.USER.value,
            "query": [{COMPARTMENT_IDS: [compartment_id]}],
            "filters": [
                {
                    "type": "auth-tokens",
                    "key": "auth_token.time_created",
                    "value": "2023/01/01",
                    "op": "greater-than",
                    "value_type": "date",
                },
                {
                    "type": "auth-tokens",
                    "key": "auth_tokens",
                    "value": 2,
                    "op": "eq",
                    "value_type": "size",
                },
            ],
        }
        session_factory = test.oci_session_factory(
            self.__class__.__name__, inspect.currentframe().f_code.co_name
        )
        policy = test.load_policy(policy_str, session_factory=session_factory)
        resources = policy.run()
        test_user_found = False
        for resource in resources:
            if resource["id"] == user_ocid:
                test_user_found = True
                break
        assert test_user_found


class IdentityUnitTest(unittest.TestCase, OciBaseTest):
    @staticmethod
    def get_policy(resource, filters=None, actions=None):
        policy = {
            "name": "test-identity",
            "query": [{"compartment_id": "ocid1.test.oc1..<unique_ID>EXAMPLE-compartmentId-Value"}],
            "resource": "oci.{0}".format(resource),
        }
        if filters:
            policy["filters"] = filters
        if actions:
            policy["actions"] = actions
        print(policy)
        return policy

    @staticmethod
    def get_tag_filter():
        return {
            "type": "value",
            "key": "freeform_tags.Cloud_Custodian",
            "value": "True",
            "op": "equal",
        }

    @staticmethod
    def get_cross_size_filter(resource):
        return {
            "type": resource,
            "key": resource,
            "value_type": "size",
            "op": "greater-than",
            "value": "0",
        }

    @staticmethod
    def get_cross_equal_size_filter(resource):
        return {
            "type": resource
            # 'key': resource
            # 'value_type': 'size',
            # 'op': 'equal',
            # 'value': '0'
        }

    @staticmethod
    def get_cross_filter_query(resource, field):
        f = resource + "." + field
        return {
            "type": resource + "s",
            "key": f,
            "value_type": "age",
            "op": "less-than",
            "value": "2",
        }

    @staticmethod
    def get_action(resource):
        method_name = "update-{0}".format(resource)
        method_param = "update_{0}_details".format(resource)
        return [
            {
                "type": method_name,
                "params": {method_param: {"freeform_tags": {"Environment": "Cloud-Custodian-Dev"}}},
            }
        ]

    @staticmethod
    def get_cross_resource_filter(cross_filter_resource):
        plural_cross_filter_resource = cross_filter_resource + "s"
        cross_filter = {
            "type": plural_cross_filter_resource,
            "key": cross_filter_resource + ".lifecycle_state",
            "value": "INACTIVE",
            "op": "equal",
        }
        return cross_filter

    def test_identity_compartment_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "compartment",
                    filters=None,
                    actions=self.get_action("compartment"),
                ),
                validate=True,
            )
        )

    def test_identity_group_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy("group", filters=None, actions=self.get_action("group")),
                validate=True,
            )
        )

    def test_identity_user_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy("user", filters=None, actions=self.get_action("user")),
                validate=True,
            )
        )

    def test_identity_api_key_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy("user", filters=None, actions=None),
                validate=True,
            )
        )

    def test_identity_auth_token_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "user",
                    filters=None,
                    actions=None,
                ),
                validate=True,
            )
        )

    def test_identity_db_credential_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "user",
                    filters=None,
                    actions=None,
                ),
                validate=True,
            )
        )

    def test_identity_customer_secret_key_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "user",
                    filters=None,
                    actions=None,
                ),
                validate=True,
            )
        )

    def test_identity_smtp_credential_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "user",
                    filters=None,
                    actions=None,
                ),
                validate=True,
            )
        )

    def test_identity_oauth_credential_schema(self):
        self.assertTrue(
            self.load_policy(
                self.get_policy(
                    "user",
                    filters=None,
                    actions=None,
                ),
                validate=True,
            )
        )
