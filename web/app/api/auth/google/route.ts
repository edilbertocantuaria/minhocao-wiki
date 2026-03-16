const DEFAULT_API_BASE_URL = 'http://localhost:8000'

function getApiBaseUrl() {
  return (process.env.API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '')
}

export async function POST(request: Request) {
  let payload: { id_token: string }

  try {
    payload = await request.json()
  } catch {
    return Response.json({ detail: 'Corpo da requisição inválido.' }, { status: 400 })
  }

  const upstreamResponse = await fetch(`${getApiBaseUrl()}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
