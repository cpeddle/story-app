package io.storyapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import io.storyapp.feature.scene.prototype.DepthScalingPrototype
import io.storyapp.feature.scene.prototype.DragonFlyAwayPrototype

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface {
                    var selectedTab by remember { mutableIntStateOf(0) }
                    Column(modifier = Modifier.fillMaxSize()) {
                        TabRow(selectedTabIndex = selectedTab) {
                            Tab(
                                selected = selectedTab == 0,
                                onClick = { selectedTab = 0 },
                                text = { Text("Depth Scale") },
                            )
                            Tab(
                                selected = selectedTab == 1,
                                onClick = { selectedTab = 1 },
                                text = { Text("Dragon Fly Away") },
                            )
                        }
                        when (selectedTab) {
                            0 -> DepthScalingPrototype(modifier = Modifier.weight(1f))
                            1 -> DragonFlyAwayPrototype(modifier = Modifier.weight(1f))
                        }
                    }
                }
            }
        }
    }
}
