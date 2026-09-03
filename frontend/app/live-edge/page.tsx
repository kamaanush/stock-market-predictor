import {
  redirect,
} from "next/navigation";

export default function LegacyLiveEdgePage() {
  redirect(
    "/dashboard?view=liveedge"
  );
}
