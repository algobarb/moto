import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_user_no_password_required():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        NoPasswordRequired=True,
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password"
    assert "PasswordCount" not in resp["Authentication"]
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_aws
def test_create_user_with_password_too_short():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpass"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Passwords length must be between 16-128 characters."


@mock_aws
def test_create_user_with_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 1
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_aws
def test_create_user_without_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1", UserName="User1", Engine="Redis", AccessString="?"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Input Authentication type: null is not in the allowed list: [password,no-password-required,iam]"
    )


@mock_aws
def test_create_user_with_iam():
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "iam"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "iam"


@mock_aws
def test_create_user_invalid_authentication_type():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="User1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "invalidtype"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Input Authentication type: invalidtype is not in the allowed list: [password,no-password-required,iam]"
    )


@mock_aws
def test_create_user_with_iam_with_passwords():
    # IAM authentication mode should not come with password fields
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "iam"},
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"] == "Password field is not allowed with authentication type: iam"
    )


@mock_aws
def test_create_user_authmode_password_with_multiple_password_fields():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="on ~* +@all",
            AuthenticationMode={"Type": "password", "Passwords": ["authmodepassword"]},
            Passwords=["requestpassword"],
            NoPasswordRequired=False,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "Passwords provided via multiple arguments. Use only one argument"
    )


@mock_aws
def test_create_user_with_authmode_password_without_passwords():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "password"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "A user with Authentication Mode: password, must have at least one password"
    )


@mock_aws
def test_create_user_with_authmode_no_password():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "no-password-required"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password-required"
    assert (
        "PasswordCount" not in resp["Authentication"]
    )  # even though optional, we don't expect it for no-password-required


@mock_aws
def test_create_user_with_no_password_required_and_authmode_nopassword():
    user_id = "user1"
    client = boto3.client("elasticache", region_name="us-east-1")
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        NoPasswordRequired=True,
        AuthenticationMode={"Type": "no-password-required"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password"
    assert (
        "PasswordCount" not in resp["Authentication"]
    )  # even though optional, we don't expect it for no-password-required


@mock_aws
def test_create_user_with_no_password_required_and_authmode_different():
    for auth_mode in ["password", "iam"]:
        client = boto3.client("elasticache", region_name="ap-southeast-1")
        with pytest.raises(ClientError) as exc:
            client.create_user(
                UserId="user1",
                UserName="user1",
                Engine="Redis",
                AccessString="on ~* +@all",
                NoPasswordRequired=True,
                AuthenticationMode={"Type": auth_mode},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameterCombination"
        assert (
            err["Message"]
            == f"No password required flag is true but provided authentication type is {auth_mode}"
        )


@mock_aws
def test_create_user_with_authmode_password():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={
            "Type": "password",
            "Passwords": ["mysecretpassthatsverylong"],
        },
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 1


@mock_aws
def test_create_user_with_authmode_password_multiple():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={
            "Type": "password",
            "Passwords": ["mysecretpassthatsverylong", "mysecretpassthatsverylong2"],
        },
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 2


@mock_aws
def test_create_user_twice():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserAlreadyExists"
    assert err["Message"] == "User user1 already exists."


@mock_aws
@pytest.mark.parametrize("engine", ["redis", "Redis", "reDis"])
def test_create_user_engine_parameter_is_case_insensitive(engine):
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine=engine,
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "iam"},
    )
    assert resp["Engine"] == engine.lower()


@mock_aws
def test_create_user_with_invalid_engine_type():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="invalidengine",
            AccessString="on ~* +@all",
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"


@mock_aws
def test_delete_user_unknown():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_user(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."


@mock_aws
def test_delete_user():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    client.delete_user(UserId="user1")

    # Initial status is 'deleting'
    resp = client.describe_users(UserId="user1")
    assert resp["Users"][0]["Status"] == "deleting"

    # User is only deleted after some time
    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    assert exc.value.response["Error"]["Code"] == "UserNotFound"


@mock_aws
def test_describe_users_initial():
    client = boto3.client("elasticache", region_name="us-east-2")
    resp = client.describe_users()

    assert len(resp["Users"]) == 1
    assert resp["Users"][0] == {
        "UserId": "default",
        "UserName": "default",
        "Status": "active",
        "Engine": "redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "no-password"},
        "ARN": f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:user:default",
    }


@mock_aws
def test_describe_users():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    resp = client.describe_users()

    assert len(resp["Users"]) == 2
    assert {
        "UserId": "user1",
        "UserName": "User1",
        "Status": "active",
        "Engine": "redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "password", "PasswordCount": 1},
        "ARN": f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:user1",
    } in resp["Users"]


@mock_aws
def test_describe_users_unknown_userid():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."


@mock_aws
def test_create_redis_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_redis_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "redis"
    cache_cluster_num_cache_nodes = 5

    resp = client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
        AutoMinorVersionUpgrade=True,
        TransitEncryptionEnabled=True,
    )
    cache_cluster = resp["CacheCluster"]

    if cache_cluster["CacheClusterId"] == cache_cluster_id:
        if cache_cluster["Engine"] == cache_cluster_engine:
            if cache_cluster["NumCacheNodes"] == 1:
                test_redis_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["CacheCluster"]["AutoMinorVersionUpgrade"] is True
    assert resp["CacheCluster"]["TransitEncryptionEnabled"] is True
    assert test_redis_cache_cluster_exist


@mock_aws
def test_create_memcached_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_memcached_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    resp = client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )
    cache_cluster = resp["CacheCluster"]

    if cache_cluster["CacheClusterId"] == cache_cluster_id:
        if cache_cluster["Engine"] == cache_cluster_engine:
            if cache_cluster["NumCacheNodes"] == 5:
                test_memcached_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_memcached_cache_cluster_exist


@mock_aws
def test_create_duplicate_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.create_cache_cluster(
            CacheClusterId=cache_cluster_id,
            Engine=cache_cluster_engine,
            NumCacheNodes=cache_cluster_num_cache_nodes,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterAlreadyExists"
    assert err["Message"] == f"Cache cluster {cache_cluster_id} already exists."


@mock_aws
def test_describe_all_cache_clusters():
    client = boto3.client("elasticache", region_name="us-east-2")

    num_clusters = 5
    match_number = 0

    for i in range(num_clusters):
        client.create_cache_cluster(
            CacheClusterId=f"test-cache-cluster-{i}",
            Engine="memcached",
            NumCacheNodes=5,
        )

    resp = client.describe_cache_clusters()
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    cache_clusters = resp["CacheClusters"]

    for i, cache_cluster in enumerate(cache_clusters):
        if cache_cluster["CacheClusterId"] == f"test-cache-cluster-{i}":
            match_number = match_number + 1

    if match_number == (num_clusters):
        assert True
    else:
        assert False


@mock_aws
def test_describe_specific_cache_clusters():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_memcached_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    client.create_cache_cluster(
        CacheClusterId="test-cache-cluster-2",
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    resp = client.describe_cache_clusters(CacheClusterId=cache_cluster_id)

    cache_clusters = resp["CacheClusters"]

    for cache_cluster in cache_clusters:
        if cache_cluster["CacheClusterId"] == cache_cluster_id:
            test_memcached_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_memcached_cache_cluster_exist


@mock_aws
def test_describe_unknown_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_id_unknown = "unknown-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.describe_cache_clusters(
            CacheClusterId=cache_cluster_id_unknown,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterNotFound"
    assert err["Message"] == f"Cache cluster {cache_cluster_id_unknown} not found."


@mock_aws
def test_delete_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    client.delete_cache_cluster(CacheClusterId=cache_cluster_id)

    resp = client.describe_cache_clusters(CacheClusterId=cache_cluster_id)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["CacheClusters"][0]["CacheClusterStatus"] == "deleting"


@mock_aws
def test_delete_unknown_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_id_unknown = "unknown-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.delete_cache_cluster(
            CacheClusterId=cache_cluster_id_unknown,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterNotFound"
    assert err["Message"] == f"Cache cluster {cache_cluster_id_unknown} not found."


@mock_aws
def test_list_tags_cache_cluster():
    conn = boto3.client("elasticache", region_name="ap-southeast-1")
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:elasticache:us-west-2:1234567890:cluster:foo"
    )
    assert result["TagList"] == []
    test_instance = conn.create_cache_cluster(
        CacheClusterId="test-cache-cluster",
        Engine="memcached",
        NumCacheNodes=2,
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
        SecurityGroupIds=["sg-1234"],
    )
    post_create_result = conn.list_tags_for_resource(
        ResourceName=test_instance["CacheCluster"]["ARN"],
    )
    assert post_create_result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]
