<template>
  <span class="transport-mode-badge">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { TransportationMode } from "../../types";

const props = defineProps<{
  mode: TransportationMode;
}>();

const labels: Record<TransportationMode, string> = {
  walking: "Walking",
  public_transport: "Public transport",
  car_taxi: "Car or taxi",
};

const label = computed(() => labels[props.mode]);
</script>
