const DEFAULT_API_BASE_URL = 'http://localhost:8000'

function getApiBaseUrl() {
  return (process.env.API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

function getAuthHeader(request: Request) {
  return request.headers.get('Authorization') || ''
}

export async function POST(request: Request) {
  let payload: unknown
  const authHeader = getAuthHeader(request)

  try {
    payload = await request.json()
  } catch {
    return Response.json({ error: 'Corpo da requisicao invalido.' }, { status: 400 })
  }

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': authHeader,
    },
    body: JSON.stringify(payload),
    cache: 'no-store',
  }).catch(() => null)

  if (!upstreamResponse) {
    return Response.json(
      { error: 'Nao foi possivel conectar a API em http://localhost:8000.' },
      { status: 502 }
    )
  }

  if (!upstreamResponse.ok) {
    const errorText = await upstreamResponse.text()

    return Response.json(
      { error: errorText || 'A API retornou um erro ao processar a mensagem.' },
      { status: upstreamResponse.status }
    )
  }

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'no-store',
    },
  })
}
