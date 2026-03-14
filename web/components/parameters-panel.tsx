'use client'

import { Settings2 } from 'lucide-react'
import { ParameterControl } from './parameter-control'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetDescription,
} from '@/components/ui/sheet'

interface Parameters {
  frequency_penalty: number
  presence_penalty: number
  temperature: number
  max_tokens: number
  n: number
  seed: number
  stop: string
}

interface ParametersPanelProps {
  parameters: Parameters
  onParametersChange: (params: Parameters) => void
}

const PARAMETER_TOOLTIPS = {
  frequency_penalty:
    'Penaliza palavras frequentes. Valores altos geram textos mais variados, valores baixos permitem repetições.',

  presence_penalty:
    'Penaliza palavras já mencionadas. Incentiva o modelo a introduzir novos conceitos.',

  temperature:
    'Controla a aleatoriedade. Baixo = respostas previsíveis. Alto = respostas criativas.',

  max_tokens:
    'Número máximo de tokens na resposta. Limita o comprimento do texto gerado.',

  n: 'Quantidade de respostas alternativas a serem geradas para o mesmo prompt.',

  seed: 'Valor para resultados reproduzíveis. Mesmo seed = mesma resposta.',

  stop: 'Palavras que interrompem a geração. Separe múltiplos valores com vírgula.',
}

export function ParametersPanel({
  parameters,
  onParametersChange,
}: ParametersPanelProps) {
  const updateParameter = <K extends keyof Parameters>(
    key: K,
    value: Parameters[K]
  ) => {
    onParametersChange({ ...parameters, [key]: value })
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-foreground"
        >
          <Settings2 className="size-5" />
          <span className="sr-only">Parâmetros do modelo</span>
        </Button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="w-full sm:w-[35vw] sm:min-w-[420px] sm:max-w-[600px] bg-card border-border overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle className="text-foreground">
            Parâmetros do Modelo
          </SheetTitle>
          <SheetDescription>
            Ajuste os parâmetros para controlar o comportamento do LLM
          </SheetDescription>
        </SheetHeader>

        <div className="w-full px-4 py-6 flex flex-col gap-6">
          <ParameterControl
            label="Temperatura"
            value={parameters.temperature}
            onChange={(v) => updateParameter('temperature', Number(v))}
            min={0}
            max={1}
            step={0.1}
            tooltip={PARAMETER_TOOLTIPS.temperature}
          />

          <ParameterControl
            label="Máximo de Tokens"
            value={parameters.max_tokens}
            onChange={(v) => updateParameter('max_tokens', Number(v))}
            min={1}
            max={4096}
            step={1}
            tooltip={PARAMETER_TOOLTIPS.max_tokens}
          />

          <ParameterControl
            label="Penalidade de Frequência"
            value={parameters.frequency_penalty}
            onChange={(v) => updateParameter('frequency_penalty', Number(v))}
            min={0}
            max={1}
            step={0.1}
            tooltip={PARAMETER_TOOLTIPS.frequency_penalty}
          />

          <ParameterControl
            label="Penalidade de Presença"
            value={parameters.presence_penalty}
            onChange={(v) => updateParameter('presence_penalty', Number(v))}
            min={0}
            max={1}
            step={0.1}
            tooltip={PARAMETER_TOOLTIPS.presence_penalty}
          />

          <ParameterControl
            label="n"
            value={parameters.n}
            onChange={(v) => updateParameter('n', Number(v))}
            min={1}
            max={5}
            step={1}
            tooltip={PARAMETER_TOOLTIPS.n}
          />

          <ParameterControl
            label="Seed"
            value={parameters.seed}
            onChange={(v) => updateParameter('seed', Number(v))}
            min={0}
            max={999999}
            step={1}
            tooltip={PARAMETER_TOOLTIPS.seed}
            type="input"
          />

          <ParameterControl
            label="Palavras de Parada"
            value={parameters.stop}
            onChange={(v) => updateParameter('stop', String(v))}
            tooltip={PARAMETER_TOOLTIPS.stop}
            type="input"
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}
