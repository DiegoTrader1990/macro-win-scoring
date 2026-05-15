"""
Alert System - Som + Webhook + Telegram
========================================
Sistema de alertas que notifica o operador quando eventos
importantes ocorrem no sistema de macro scoring.

Tipos de alerta:
- Sinal mudou (ex: NEUTRO → COMPRA)
- Sinal forte (score acima do threshold)
- Divergencia detectada (score vs preco)
- Recuperacao intraday detectada
- Reversao de preco detectada

Canais de notificacao:
- Som: Beep via JavaScript AudioContext (para o dashboard web)
- Webhook: POST HTTP para URL configurada
- Telegram: Mensagem via Bot API

v5.0 - Componente do sistema de macro scoring
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AlertSystem:
    """
    Sistema de alertas com som, webhook e Telegram.

    Verifica condicoes de alerta e notifica pelos canais configurados.
    Inclui cooldown entre alertas para evitar spam.

    Uso tipico:
        alerts = AlertSystem(config.ALERT_CONFIG)
        should_alert = alerts.check_and_alert(
            signal_change=True,
            signal_type="COMPRA",
            score=45,
            divergence=div_result,
            recovery=rec_result,
            reversal=rev_result,
        )
        # Se should_alert["alert_fired"], o alerta foi emitido
    """

    def __init__(self, config: dict = None):
        """
        Inicializa o sistema de alertas.

        Args:
            config: Dict com configuracoes (ALERT_CONFIG).
                    Campos esperados:
                    - enabled: ativa/desativa alertas (default: True)
                    - cooldown_seconds: intervalo minimo entre alertas (default: 120)
                    - sound_enabled: ativa som (default: True)
                    - webhook_enabled: ativa webhook (default: False)
                    - webhook_url: URL do webhook
                    - telegram_enabled: ativa Telegram (default: False)
                    - telegram_bot_token: token do bot Telegram
                    - telegram_chat_id: chat ID do Telegram
                    - alert_on_signal_change: alerta quando sinal muda (default: True)
                    - alert_on_strong_signal: alerta quando sinal forte (default: True)
                    - alert_on_divergence: alerta quando divergencia detectada (default: True)
                    - alert_on_recovery: alerta quando recuperacao detectada (default: True)
                    - alert_on_reversal: alerta quando reversao detectada (default: True)
                    - strong_signal_threshold: score acima = forte (default: 50)
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.cooldown = self.config.get("cooldown_seconds", 120)
        self.sound_enabled = self.config.get("sound_enabled", True)
        self.webhook_enabled = self.config.get("webhook_enabled", False)
        self.webhook_url = self.config.get("webhook_url", "")
        self.telegram_enabled = self.config.get("telegram_enabled", False)
        self.telegram_bot_token = self.config.get("telegram_bot_token", "")
        self.telegram_chat_id = self.config.get("telegram_chat_id", "")
        self.alert_on_signal_change = self.config.get("alert_on_signal_change", True)
        self.alert_on_strong_signal = self.config.get("alert_on_strong_signal", True)
        self.alert_on_divergence = self.config.get("alert_on_divergence", True)
        self.alert_on_recovery = self.config.get("alert_on_recovery", True)
        self.alert_on_reversal = self.config.get("alert_on_reversal", True)
        self.strong_threshold = self.config.get("strong_signal_threshold", 50)

        # Timestamp do ultimo alerta
        self._last_alert_time: Optional[datetime] = None

        # Historico de alertas
        self._alert_history = []
        self._max_history = 100

        # Ultimo sinal para detectar mudancas
        self._last_signal_type: Optional[str] = None

        logger.info(
            f"AlertSystem inicializado: sound={self.sound_enabled}, "
            f"webhook={self.webhook_enabled}, telegram={self.telegram_enabled}, "
            f"cooldown={self.cooldown}s, enabled={self.enabled}"
        )

    def check_and_alert(self, signal_change: bool = False,
                        signal_type: str = "NEUTRO",
                        score: float = 0,
                        divergence: dict = None,
                        recovery: dict = None,
                        reversal: dict = None) -> Dict:
        """
        Verifica condicoes de alerta e dispara se necessario.

        Ordem de prioridade:
        1. Reversao de preco detectada (CRITICO)
        2. Recuperacao intraday detectada (ALTO)
        3. Sinal mudou (MEDIO)
        4. Sinal forte (MEDIO)
        5. Divergencia detectada (MEDIO)

        Args:
            signal_change: Se o sinal mudou desde a ultima leitura.
            signal_type: Tipo do sinal atual.
            score: Score macro atual.
            divergence: Resultado da deteccao de divergencia.
            recovery: Resultado da deteccao de recuperacao.
            reversal: Resultado da deteccao de reversao de preco.

        Returns:
            Dict com alert_fired, alert_type, message, channels_used.
        """
        if not self.enabled:
            return {
                "alert_fired": False,
                "alert_type": None,
                "message": "",
                "channels_used": [],
                "reason": "Sistema de alertas desabilitado",
            }

        now = datetime.now()

        # Verifica cooldown
        if self._last_alert_time is not None:
            elapsed = (now - self._last_alert_time).total_seconds()
            if elapsed < self.cooldown:
                remaining = self.cooldown - elapsed
                return {
                    "alert_fired": False,
                    "alert_type": None,
                    "message": "",
                    "channels_used": [],
                    "reason": f"Cooldown ativo: {remaining:.0f}s restantes",
                }

        # Avalia condicoes de alerta por prioridade
        alert_type = None
        alert_priority = 0
        alert_message = ""

        # 1. Reversao de preco (prioridade maxima)
        if self.alert_on_reversal and reversal and isinstance(reversal, dict):
            if reversal.get("detected", False):
                alert_type = "PRICE_REVERSAL"
                alert_priority = 5
                direction = reversal.get("direction", "")
                strength = reversal.get("strength", "")
                alert_message = (
                    f"⚡ REVERSAO DE PRECO ({direction}) - {strength}\n"
                    f"Score: {score:+.0f} | Tipo: {reversal.get('type', '')}\n"
                    f"{reversal.get('description', '')}\n"
                    f"Acao: {reversal.get('action', '')}"
                )

        # 2. Recuperacao intraday
        if (alert_priority < 5 and self.alert_on_recovery
                and recovery and isinstance(recovery, dict)):
            if recovery.get("detected", False):
                alert_type = "RECOVERY"
                alert_priority = 4
                strength = recovery.get("strength", "")
                alert_message = (
                    f"🔄 RECUPERACAO INTRADAY - {strength}\n"
                    f"Score: {score:+.0f} | Recuperou {recovery.get('recovery_pct', 0):.0f}%\n"
                    f"{recovery.get('description', '')}"
                )

        # 3. Sinal mudou
        if alert_priority < 4 and self.alert_on_signal_change and signal_change:
            alert_type = "SIGNAL_CHANGE"
            alert_priority = 3
            prev_signal = self._last_signal_type or "N/A"
            alert_message = (
                f"🔔 SINAL MUDOU: {prev_signal} → {signal_type}\n"
                f"Score: {score:+.0f}"
            )

        # 4. Sinal forte
        if alert_priority < 3 and self.alert_on_strong_signal:
            if abs(score) >= self.strong_threshold:
                alert_type = "STRONG_SIGNAL"
                alert_priority = 2
                direction = "ALTA" if score > 0 else "BAIXA"
                alert_message = (
                    f"🚨 SINAL FORTE DE {direction}\n"
                    f"Score: {score:+.0f} (threshold: ±{self.strong_threshold})\n"
                    f"Tipo: {signal_type}"
                )

        # 5. Divergencia
        if (alert_priority < 2 and self.alert_on_divergence
                and divergence and isinstance(divergence, dict)):
            div_type = divergence.get("type", "")
            if div_type not in ("NEUTRO", "INDEFINIDO", "SEM_DIVERGENCIA"):
                alert_type = "DIVERGENCE"
                alert_priority = 1
                alert_message = (
                    f"⚠️ DIVERGENCIA: {divergence.get('label', div_type)}\n"
                    f"Score: {score:+.0f}\n"
                    f"{divergence.get('description', '')}"
                )

        # Atualiza ultimo sinal
        self._last_signal_type = signal_type

        # Se nenhuma condicao de alerta foi atendida
        if alert_type is None:
            return {
                "alert_fired": False,
                "alert_type": None,
                "message": "",
                "channels_used": [],
                "reason": "Nenhuma condicao de alerta atendida",
            }

        # Dispara alertas pelos canais configurados
        channels_used = []
        full_message = self._format_message(alert_type, alert_message, score, signal_type)

        if self.sound_enabled:
            channels_used.append("sound")

        if self.webhook_enabled and self.webhook_url:
            self._send_webhook(full_message)
            channels_used.append("webhook")

        if self.telegram_enabled and self.telegram_bot_token and self.telegram_chat_id:
            self._send_telegram(full_message)
            channels_used.append("telegram")

        # Atualiza cooldown
        self._last_alert_time = now

        # Registra no historico
        self._alert_history.append({
            "timestamp": now,
            "alert_type": alert_type,
            "message": full_message,
            "channels": channels_used,
            "score": score,
            "signal_type": signal_type,
        })
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        logger.info(
            f"Alerta disparado: type={alert_type}, "
            f"channels={channels_used}, "
            f"score={score:+.0f}"
        )

        return {
            "alert_fired": True,
            "alert_type": alert_type,
            "message": full_message,
            "channels_used": channels_used,
            "priority": alert_priority,
        }

    def _format_message(self, alert_type: str, core_message: str,
                        score: float, signal_type: str) -> str:
        """
        Formata a mensagem de alerta com informacoes completas.

        Args:
            alert_type: Tipo do alerta.
            core_message: Mensagem principal ja formatada.
            score: Score macro.
            signal_type: Tipo do sinal atual.

        Returns:
            Mensagem formatada completa.
        """
        now = datetime.now()
        timestamp_str = now.strftime("%H:%M:%S")

        header = f"📊 MACRO WIN SCORING - {timestamp_str}\n"
        separator = "─" * 30 + "\n"
        footer = (
            f"\n{separator}"
            f"Score: {score:+.1f} | Sinal: {signal_type}\n"
            f"Tipo Alerta: {alert_type}"
        )

        return header + separator + core_message + footer

    def _play_sound(self) -> str:
        """
        Gera codigo JavaScript para emitir beep no navegador.

        Usa a Web Audio API (AudioContext) para gerar um beep
        simples sem necessidade de arquivos de audio externos.

        Returns:
            String com codigo JavaScript para executar no navegador.
        """
        js_code = """
        (function() {
            try {
                var ctx = new (window.AudioContext || window.webkitAudioContext)();
                var oscillator = ctx.createOscillator();
                var gainNode = ctx.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(ctx.destination);

                // Configuracao do beep
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(880, ctx.currentTime);
                oscillator.frequency.setValueAtTime(1100, ctx.currentTime + 0.1);
                oscillator.frequency.setValueAtTime(880, ctx.currentTime + 0.2);

                gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

                oscillator.start(ctx.currentTime);
                oscillator.stop(ctx.currentTime + 0.4);

                setTimeout(function() {
                    ctx.close();
                }, 500);
            } catch(e) {
                console.error('Erro ao reproduzir som de alerta:', e);
            }
        })();
        """
        return js_code.strip()

    def _send_webhook(self, message: str) -> bool:
        """
        Envia alerta via webhook (HTTP POST).

        Args:
            message: Mensagem do alerta.

        Returns:
            True se enviado com sucesso, False caso contrario.
        """
        if not self.webhook_url:
            return False

        try:
            payload = json.dumps({
                "text": message,
                "alert_type": "macro_win_scoring",
                "timestamp": datetime.now().isoformat(),
            }).encode("utf-8")

            req = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info("Webhook enviado com sucesso")
                    return True
                else:
                    logger.warning(f"Webhook retornou status {response.status}")
                    return False

        except urllib.error.URLError as e:
            logger.error(f"Erro ao enviar webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado no webhook: {e}")
            return False

    def _send_telegram(self, message: str) -> bool:
        """
        Envia alerta via Telegram Bot API.

        Args:
            message: Mensagem do alerta.

        Returns:
            True se enviado com sucesso, False caso contrario.
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        try:
            url = (
                f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            )

            payload = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info("Telegram enviado com sucesso")
                    return True
                else:
                    logger.warning(f"Telegram retornou status {response.status}")
                    return False

        except urllib.error.URLError as e:
            logger.error(f"Erro ao enviar Telegram: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado no Telegram: {e}")
            return False

    def get_alert_html(self, alert_type: str, message: str) -> str:
        """
        Retorna HTML para notificacao de alerta no dashboard.

        Gera um elemento HTML estilizado que pode ser injetado
        no dashboard para exibir o alerta visualmente.

        Args:
            alert_type: Tipo do alerta.
            message: Mensagem do alerta.

        Returns:
            String com HTML completo da notificacao.
        """
        # Cores por tipo de alerta
        color_map = {
            "PRICE_REVERSAL": "#FF9800",
            "RECOVERY": "#66BB6A",
            "SIGNAL_CHANGE": "#4FC3F7",
            "STRONG_SIGNAL": "#FF1744",
            "DIVERGENCE": "#FFD600",
        }
        bg_color = color_map.get(alert_type, "#78909C")

        # Icones por tipo
        icon_map = {
            "PRICE_REVERSAL": "⚡",
            "RECOVERY": "🔄",
            "SIGNAL_CHANGE": "🔔",
            "STRONG_SIGNAL": "🚨",
            "DIVERGENCE": "⚠️",
        }
        icon = icon_map.get(alert_type, "📢")

        # Escapa aspas simples para HTML
        safe_message = message.replace("'", "\\'").replace("\n", "<br>")

        html = f"""
        <div id="alert-notification" style="
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            background: linear-gradient(135deg, {bg_color}22, {bg_color}44);
            border: 2px solid {bg_color};
            border-radius: 12px;
            padding: 16px 20px;
            max-width: 360px;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
            box-shadow: 0 4px 20px {bg_color}44;
            animation: alertSlideIn 0.3s ease-out;
        ">
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 8px;
            ">
                <span style="font-size: 24px;">{icon}</span>
                <span style="
                    font-size: 14px;
                    font-weight: 700;
                    color: {bg_color};
                    text-transform: uppercase;
                    letter-spacing: 1px;
                ">{alert_type.replace('_', ' ')}</span>
                <button onclick="document.getElementById('alert-notification').remove()"
                    style="
                        margin-left: auto;
                        background: none;
                        border: none;
                        color: #888;
                        cursor: pointer;
                        font-size: 16px;
                    ">&times;</button>
            </div>
            <div style="
                font-size: 12px;
                line-height: 1.5;
                color: #b0b0b0;
            ">{safe_message}</div>
        </div>
        <style>
            @keyframes alertSlideIn {{
                from {{ transform: translateX(100%); opacity: 0; }}
                to {{ transform: translateX(0); opacity: 1; }}
            }}
        </style>
        """
        return html.strip()

    def get_sound_javascript(self) -> str:
        """
        Retorna o codigo JavaScript para reproduzir o beep de alerta.

        Conveniente para ser injetado no dashboard web quando
        um alerta precisa ser sonoro.

        Returns:
            String com codigo JavaScript.
        """
        return self._play_sound()

    def get_recent_alerts(self, last_n: int = 20) -> list:
        """
        Retorna os alertas mais recentes.

        Args:
            last_n: Numero de alertas a retornar.

        Returns:
            Lista de dicts com detalhes de cada alerta.
        """
        return self._alert_history[-last_n:]

    def get_status(self) -> Dict:
        """
        Retorna o status atual do sistema de alertas.

        Returns:
            Dict com configuracoes e estado.
        """
        cooldown_remaining = 0
        if self._last_alert_time is not None:
            elapsed = (datetime.now() - self._last_alert_time).total_seconds()
            cooldown_remaining = max(0, self.cooldown - elapsed)

        return {
            "enabled": self.enabled,
            "sound_enabled": self.sound_enabled,
            "webhook_enabled": self.webhook_enabled,
            "telegram_enabled": self.telegram_enabled,
            "cooldown_seconds": self.cooldown,
            "cooldown_remaining": round(cooldown_remaining, 1),
            "total_alerts_fired": len(self._alert_history),
            "last_signal": self._last_signal_type,
            "alert_conditions": {
                "signal_change": self.alert_on_signal_change,
                "strong_signal": self.alert_on_strong_signal,
                "divergence": self.alert_on_divergence,
                "recovery": self.alert_on_recovery,
                "reversal": self.alert_on_reversal,
            },
        }

    def reset(self) -> None:
        """Reseta o sistema de alertas, limpando cooldown e historico."""
        self._last_alert_time = None
        self._last_signal_type = None
        self._alert_history = []
        logger.info("AlertSystem resetado")
