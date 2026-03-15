const DEFAULT_API_BASE_URL = 'http://localhost:8000'

function getApiBaseUrl() {
  return (process.env.API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

function getAuthHeader(request: Request) {
  return request.headers.get('Authorization') || ''
}

interface RouteContext {
  params: Promise<{ id: string }>
}

// GET /conversations/{id} - Obter mensagens de uma conversa
export async function GET(request: Request, context: RouteContext) {
  const { id } = await context.params
  const authHeader = getAuthHeader(request)

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/conversations/${id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authHeader,
    },
    cache: 'no-store',
  }).catch(() => null)

  if (!upstreamResponse) {
    return Response.json(
      { detail: 'Não foi possível conectar à API.' },
      { status: 502 }
    )
  }

  const data = await upstreamResponse.json()

  return Response.json(data, { status: upstreamResponse.status })
}

// DELETE /conversations/{id} - Deletar uma conversa
export async function DELETE(request: Request, context: RouteContext) {
  const { id } = await context.params
  const authHeader = getAuthHeader(request)

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/conversations/${id}`, {
    method: 'DELETE',
    headers: {
      'Authorization': authHeader,
    },
    cache: 'no-store',
  }).catch(() => null)

  if (!upstreamResponse) {
    return Response.json(
      { detail: 'Não foi possível conectar à API.' },
      { status: 502 }
    )
  }

  if (upstreamResponse.status === 204) {
    return new Response(null, { status: 204 })
  }

  const data = await upstreamResponse.json()

  return Response.json(data, { status: upstreamResponse.status })
}
