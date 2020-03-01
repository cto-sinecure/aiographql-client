import asyncio

import pytest
from cafeteria.asyncio.callbacks import CallbackRegistry
from graphql import GraphQLSyntaxError

from aiographql.client import (
    GraphQLClientException,
    GraphQLClientValidationException,
    GraphQLRequest,
    GraphQLSubscription,
    GraphQLSubscriptionEventType,
)

# noinspection SpellCheckingInspection
pytestmark = pytest.mark.asyncio


async def test_simple_anonymous_post(client, headers, query_city, query_output):
    request = GraphQLRequest(query=query_city, headers=headers)
    response = await client.post(request)
    assert response.data == query_output


async def test_simple_anonymous_query(client, headers, query_city, query_output):
    request = GraphQLRequest(query=query_city, headers=headers)
    response = await client.query(request)
    assert response.data == query_output


async def test_invalid_query_schema(client, headers, invalid_query_schema):
    request = GraphQLRequest(query=invalid_query_schema, headers=headers)
    with pytest.raises(GraphQLClientValidationException) as excinfo:
        _ = await client.query(request)
    message = str(excinfo.value)
    assert (
        """Query validation failed

Cannot query field 'citeee' on type 'query_root'. Did you mean 'city'?

GraphQL request:3:11
2 |         query{
3 |           citeee {
  |           ^
4 |             id"""
        == message
    )


async def test_invalid_query_syntax(client, headers, invalid_query_syntax):
    request = GraphQLRequest(query=invalid_query_syntax, headers=headers)
    with pytest.raises(GraphQLSyntaxError):
        _ = await client.query(request)


async def test_invalid_method(client, headers, query_city):
    request = GraphQLRequest(query=query_city, headers=headers)
    with pytest.raises(GraphQLClientException):
        _ = await client.query(method="PUT", request=request)


async def test_mutation(client, headers, mutation_city, mutation_output):
    request = GraphQLRequest(query=mutation_city, headers=headers)
    response = await client.query(request)
    assert response.data == mutation_output


async def test_subscription(
    client, headers, subscription_query, mutation_city, city_name
):
    request = GraphQLRequest(query=subscription_query, headers=headers)
    callbacks = CallbackRegistry()
    m = []

    def callback(data):
        assert "city" in data
        m.append(data)
        if len(m) > 1:
            city = data.get("city")[0]
            assert city.get("name") == city_name
            subscription.unsubscribe()

    callbacks.register(
        GraphQLSubscriptionEventType.DATA, lambda event: callback(event.payload.data)
    )

    subscription: GraphQLSubscription = await client.subscribe(
        request=request, callbacks=callbacks, headers=headers
    )

    await asyncio.sleep(0.1)

    request = GraphQLRequest(query=mutation_city, headers=headers)
    _ = await client.query(request)

    try:
        await asyncio.wait([subscription.task], timeout=1)
        assert len(m) == 2
    except TimeoutError:
        pytest.fail("Subscriptions timed out before receiving expected messages")
