const DEFAULT_API_BASE_URL = 'http://localhost:8000'

function getApiBaseUrl() {
  return (process.env.API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

function getAuthHeader(request: Request) {
  return request.headers.get('Authorization') || ''
}

// GET /conversations - Listar conversas
export async function GET(request: Request) {
  const authHeader = getAuthHeader(request)

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/conversations`, {
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

// POST /conversations - Criar conversa
export async function POST(request: Request) {
  const authHeader = getAuthHeader(request)

  let payload: { title?: string | null }

  try {
    payload = await request.json()
  } catch {
    payload = { title: null }
  }

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/conversations`, {
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
      { detail: 'Não foi possível conectar à API.' },
      { status: 502 }
    )
  }

  const data = await upstreamResponse.json()

  return Response.json(data, { status: upstreamResponse.status })
}
