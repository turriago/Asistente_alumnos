export class Challenge {
  constructor() {
    this.state = "idle";
    this.sequence = [];
    this.index = 0;
    this.waitingRelease = false;
    this.lastAccepted = null;
    this.deadline = 0;
    this.timeoutMs = 12000;
  }

  makeSequence() {
    const numbers = [];
    for (let i = 0; i < 3; i += 1) {
      const choices = [];
      for (let n = 1; n <= 10; n += 1) {
        if (!numbers.length || n !== numbers[numbers.length - 1]) choices.push(n);
      }
      numbers.push(choices[Math.floor(Math.random() * choices.length)]);
    }
    return numbers;
  }

  start(now) {
    if (this.state === "challenge" || this.state === "success") return false;
    this.state = "challenge";
    this.sequence = this.makeSequence();
    this.index = 0;
    this.waitingRelease = false;
    this.lastAccepted = null;
    this.deadline = now + this.timeoutMs;
    return true;
  }

  reset() {
    this.state = "idle";
    this.sequence = [];
    this.index = 0;
    this.waitingRelease = false;
    this.lastAccepted = null;
    this.deadline = 0;
  }

  get target() {
    if (this.state !== "challenge" || this.waitingRelease) return null;
    return this.sequence[this.index] ?? null;
  }

  remaining(now) {
    if (this.state !== "challenge") return 0;
    return Math.max(0, this.deadline - now);
  }

  observe(now, gesture) {
    if (this.state !== "challenge") return this.view(now);
    if (now > this.deadline) {
      this.state = "failed";
      return this.view(now);
    }
    if (this.waitingRelease) {
      if (gesture == null || gesture !== this.lastAccepted) {
        this.waitingRelease = false;
        this.deadline = now + this.timeoutMs;
      }
      return this.view(now);
    }
    const target = this.sequence[this.index];
    if (target != null && gesture === target) {
      this.lastAccepted = target;
      this.index += 1;
      if (this.index >= this.sequence.length) {
        this.state = "success";
      } else {
        this.waitingRelease = true;
        this.deadline = now + this.timeoutMs;
      }
    }
    return this.view(now);
  }

  view(now) {
    const total = this.sequence.length || 3;
    const remaining = this.remaining(now);
    let message = "Pulsa Iniciar prueba cuando se vea tu rostro.";
    if (this.state === "success") message = "Su prueba fue exitosa.";
    else if (this.state === "failed") message = "Tiempo agotado. Pulsa Nueva prueba.";
    else if (this.state === "challenge" && this.waitingRelease) {
      message = `Bien (${this.index}/${total}). Baja las manos para el siguiente número.`;
    } else if (this.state === "challenge" && this.target != null) {
      const seconds = Math.max(1, Math.ceil(remaining / 1000));
      message = `Muestra ${this.target} con los dedos (${this.index + 1}/${total}). Te quedan ${seconds}s.`;
    }
    return {
      state: this.state,
      target: this.target,
      step: Math.min(this.index + 1, total),
      total,
      remaining,
      waitingRelease: this.waitingRelease,
      message,
    };
  }
}
